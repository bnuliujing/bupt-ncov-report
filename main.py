import argparse
import html
import json
import logging
import os
import re
import sys
import traceback
from typing import Dict, Optional, List, Any

import requests

# 该变量用于给每一个设置项生成文档。
# 如果您无法设置环境变量、命令行参数，可以在此处指定默认值；详情参考文档。
CONFIG_SCHEMA = {
    'BUPT_SSO_USER': {
        'description': '您登录北师大门户（https://one.bnu.edu.cn/）时使用的用户名，通常是您的学工号',
        'for_short': '北师大账号',
        'default': None,
    },
    'BUPT_SSO_PASS': {
        'description': '您登录北师大门户（https://one.bnu.edu.cn/）时使用的密码',
        'for_short': '北师大密码',
        'default': None,
    },
    'TG_BOT_TOKEN': {
        'description': '（可选）如果您需要把执行结果通过 Telegram 机器人告知，'
                       '请设为您的 Telegram 机器人的 API Token',
        'for_short': 'Bot Token',
        'default': None,
    },
    'TG_CHAT_ID': {
        'description': '（可选）如果您需要把执行结果通过 Telegram 机器人告知，'
                       '请设为您自己的用户 id',
        'for_short': '用户 ID',
        'default': None,
    },
    'BNR_LOG_PATH': {
        'description': '（可选）日志文件存放的路径，未设置则不输出日志文件。（注意日志中可能有敏感信息）',
        'for_short': '路径',
        'default': None,
    },
}
SCRIPT_DOC = {
    'description': '自动填写北师大”疫情防控通“的每日上报信息。',
}

# LOGIN_API = 'https://app.bupt.edu.cn/uc/wap/login/check'
# REPORT_PAGE = 'https://app.bupt.edu.cn/ncov/wap/default/index'
# REPORT_API = 'https://app.bupt.edu.cn/ncov/wap/default/save'

LOGIN_API = 'https://onewechat.bnu.edu.cn/uc/wap/login/check'
REPORT_PAGE = 'https://onewechat.bnu.edu.cn/ncov/wap/default/index'
REPORT_API = 'https://onewechat.bnu.edu.cn/ncov/wap/default/save'

# 不能再短了，再短肯定是出 bug 了
REASONABLE_LENGTH = 24
TIMEOUT_SECOND = 10

# 用于存储程序运行所需要的配置。详情请参考文档。
g_config: Dict[str, Optional[str]] = {}
logger = logging.getLogger('bupt_ncov_report')

# 初始化 session
session = requests.Session()


def get_config() -> Dict[str, Optional[str]]:
    return g_config


def set_session(new_session) -> None:
    """
    修改 session 变量，以方便测试。
    :param new_session: 新的 Session 对象
    :return: None
    """

    global session
    session = new_session


def initialize_session(session: requests.Session) -> None:
    """
    初始化 requests 的 Session 对象。
    :param session: requests.Session
    :return: None
    """
    session.timeout = TIMEOUT_SECOND


def initialize_config(config: dict, schema: dict) -> None:
    """
    通过 schema 来初始化 config 变量。
    :param config: config 变量
    :return: None
    """
    for key in schema.keys():
        config[key] = schema[key]['default']


def fill_config_with_env(config: Dict[str, Optional[str]], environ: Any) -> None:
    """
    从环境变量中获取配置的值，填写到 config 变量中。
    :param config: config 变量
    :return: None
    """
    for name in [*config.keys()]:
        if name in environ and environ[name] != '':
            config[name] = environ[name]


def fill_config_with_argparse(config: Dict[str, Optional[str]], config_schema: dict, argv: List[str]):
    """
    从命令行参数中获取配置，填入 config 中。
    （本函数可能会导致整个程序退出）
    :param config: config 变量
    :return: 参数列表
    """
    # 使用 argparse 来解析命令行参数
    parser = argparse.ArgumentParser(
        description=SCRIPT_DOC['description'],
    )
    for name, schema in config_schema.items():
        # 将形如 FOO_BAR 的名字转换为 --foo-bar，添加为命令行参数
        parser.add_argument(
            '--' + name.lower().replace('_', '-'),
            type=str,
            help=schema['description'],
            metavar=f'<{schema["for_short"]}>',
            dest=name,
            default=schema['default'],
        )

    # 解析命令行参数，将被指定的项填写到 config 变量中
    args = vars(parser.parse_args(argv))

    # 删掉非字符串类型和空字符串
    args = {k: v for k, v in args.items() if isinstance(v, str) and len(v) > 0}

    for name in config_schema.keys():
        if name in args:
            config[name] = args[name]


def config_type_consistency(config: Dict[str, Optional[str]]) -> None:
    """
    将 config 变量中为空字符串、或不为字符串的值设为 None；
    提高类型一致性，方便之后使用 config 变量。
    :return: None
    """
    for name in [*config.keys()]:
        if not isinstance(config[name], str) or config[name] == '':
            config[name] = None


def check_config(config: Dict[str, Optional[str]]) -> None:
    """
    检查程序配置是否正确；如不正确则抛出异常。
    :return: None
    """

    # 检查 BUPT SSO 用户名、密码
    for key in ('BUPT_SSO_USER', 'BUPT_SSO_PASS'):
        if config[key] is None:
            raise ValueError(f'配置 {key} 未设置。缺少此配置，该脚本无法自动登录北师大网站。')

    # 检查 Telegram 的环境变量是否已经设置
    if (config['TG_BOT_TOKEN'] is None) != (config['TG_CHAT_ID'] is None):
        raise ValueError('TG_BOT_TOKEN 和 TG_CHAT_ID 必须同时设置，否则程序无法正确运行。')


def initialize_logger(logger: logging.Logger, log_file: Optional[str]) -> None:
    """
    初始化传入的 Logger 对象，
    将 INFO 以上的日志输出到屏幕，将所有日志存入文件。
    :param logger: Logger 对象
    :param log_file: 日志文件路径
    :return: None
    """
    logger.setLevel(logging.DEBUG)

    # 将日志输出到控制台
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    logger.addHandler(sh)

    # 将日志输出到文件
    if log_file:
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(fh)


def match_re_group1(re_str: str, text: str) -> str:
    """
    在 text 中匹配正则表达式 re_str，返回第 1 个捕获组（即首个用括号包住的捕获组）
    :param re_str: 正则表达式（字符串）
    :param text: 要被匹配的文本
    :return: 第 1 个捕获组
    """
    match = re.search(re_str, text)
    if match is None:
        raise ValueError(f'在文本中匹配 {re_str} 失败，没找到任何东西。\n请阅读脚本文档中的“使用前提”部分。')

    return match.group(1)


def extract_post_data(html: str) -> Dict[str, str]:
    """
    从上报页面的 HTML 中，提取出上报 API 所需要填写的参数。
    :return: 最终 POST 的参数（使用 dict 表示）
    """
    new_data = match_re_group1(r'var def = (\{.+\});', html)
    old_data = match_re_group1(r'oldInfo: (\{.+\}),', html)

    # 检查数据是否足够长
    if len(old_data) < REASONABLE_LENGTH or len(new_data) < REASONABLE_LENGTH:
        logger.debug(f'\nold_data: {old_data}\nnew_data: {new_data}')
        raise ValueError('获取到的数据过短。请阅读脚本文档的“使用前提”部分')

    # 用原页面的“def”变量的值，覆盖掉“oldInfo”变量的值
    old_data, new_data = json.loads(old_data), json.loads(new_data)
    old_data.update(new_data)
    return old_data


def do_ncov_report(config: Dict[str, Optional[str]]) -> str:
    """
    进行信息上报的工作函数，包含本脚本主要逻辑。
    :return: 上报 API 的返回内容。
    """
    # 登录北师大 nCoV 上报网站
    logger.info('登录北师大 nCoV 上报网站')
    login_res = session.post(LOGIN_API, data={
        'username': g_config['BUPT_SSO_USER'],
        'password': g_config['BUPT_SSO_PASS'],
    })
    if login_res.status_code != 200:
        logger.debug(f'登录页：\n'
                     f'status code: {login_res.status_code}\n'
                     f'url: {login_res.url}')
        raise RuntimeError('登录 API 返回的 HTTP 状态码不是 200。')

    # 获取上报页面的数据
    report_page_res = session.get(REPORT_PAGE)
    logger.debug(f'报告页：\n'
                 f'status code: {report_page_res.status_code}\n'
                 f'url: {report_page_res.url}')
    if report_page_res.status_code != 200:
        raise RuntimeError('上报页面的 HTTP 状态码不是 200。')
    page_html = report_page_res.text
    if '每日上报' not in page_html:
        raise RuntimeError('上报页面的 HTML 中没有找到“每日上报”。')

    # 从上报页面中提取 POST 的参数
    post_data = extract_post_data(page_html)
    logger.debug(f'最终提交参数：{json.dumps(post_data)}')

    # 最终 POST
    report_api_res = session.post(REPORT_API, post_data)
    if report_api_res.status_code != 200:
        raise RuntimeError('上报 API 返回的 HTTP 状态码不是 200。')

    return report_api_res.text


def main(*wtf, **kwwtf) -> None:
    """
    入口函数。可部署于 GCP Cloud Function/AWS Lambda 等云函数平台，也可以自行运行。
    该函数读取程序配置，并尝试调用工作函数；
    该函数随后获取工作函数的返回值或异常内容，通过 Telegram 机器人发送给用户。
    :return: None
    """

    # 读取程序配置，并检查配置是否出错
    initialize_session(session)
    initialize_config(g_config, CONFIG_SCHEMA)
    fill_config_with_env(g_config, os.environ)
    fill_config_with_argparse(g_config, CONFIG_SCHEMA, sys.argv[1:])
    config_type_consistency(g_config)
    check_config(g_config)

    # 初始化日志
    initialize_logger(logger, g_config['BNR_LOG_PATH'])

    # 运行工作函数
    logger.info('运行工作函数')
    success = True
    try:
        res = do_ncov_report(g_config)
    except:
        success = False
        res = traceback.format_exc()

    # 生成消息并打印到控制台
    if success:
        msg = f'[bupt-ncov-report] <b>成功：</b>服务器的返回是：\n\n' \
              f'<pre>{html.escape(res)}</pre>'
    else:
        msg = f'[bupt-ncov-report] <b>失败：</b>发生如下异常：\n\n' \
              f'<pre>{html.escape(res)}</pre>'
    logger.info(msg)

    # 如果用户指定了 Telegram 相关信息，就把消息通过 Telegram 发送给用户
    logger.info('将运行结果通过 Telegram 机器人发送')
    if g_config['TG_BOT_TOKEN'] is not None:
        try:
            tg_res = session.post(f'https://api.telegram.org/bot{g_config["TG_BOT_TOKEN"]}/sendMessage', json={
                'chat_id': g_config['TG_CHAT_ID'],
                'text': msg,
                'parse_mode': 'HTML',
            }, timeout=TIMEOUT_SECOND)

            tg_res = tg_res.json()
            if 'ok' not in tg_res:
                raise ValueError('Telegram API 的返回值很奇怪。')
            if not tg_res['ok']:
                raise ValueError(f'Telegram API 调用失败，可能您的 Token 或 chat id 配置有误。'
                                 f'API 的返回是：\n{tg_res}')

        except:
            # 将 Telegram 机器人的错误也打印下来
            logger.error('调用 Telegram API 时发生错误', exc_info=True)


if __name__ == '__main__':
    main()
