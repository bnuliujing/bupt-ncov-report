# BUPT 疫情防控通 自动上报脚本

- Now it works on BNU... just use your [one.bnu.eud.cn](one.bnu.edu.cn) username and password and follow the description below.

[![单元&功能测试     ](https://github.com/ipid/bupt-ncov-report/workflows/%E5%8D%95%E5%85%83&%E5%8A%9F%E8%83%BD%E6%B5%8B%E8%AF%95%20%20%20%20%20/badge.svg)](https://github.com/ipid/bupt-ncov-report/actions) [![Coverage 状态](https://coveralls.io/repos/github/ipid/bupt-ncov-report/badge.svg?branch=master)](https://coveralls.io/github/ipid/bupt-ncov-report?branch=master)

该脚本可以帮助您操作北邮「疫情防控通」，自动完成每日上报。



## 特性

- 既可以部署在服务器上，也可以部署在 GCP Cloud Function、AWS Lambda 或阿里云、腾讯云云函数等支持 Python 的云函数平台上。
- 上报完成后，可通过 **Telegram 机器人**来接收上报结果，方便您得知自动上报是否成功

![Telegram 提醒](https://i.loli.net/2020/02/06/a8vimqWH7lVInX6.png)

- 可输出**日志文件**，得知运行失败原因
- 单元测试覆盖 80% 的代码




## 使用前提

- 该脚本的工作方式为：爬取您上一次上报的信息，然后自动上报同样的信息。因此，使用前，您需要保证**昨天**~~_（格林威治时间）_~~（北京时间）已经正确填报了信息。如果您尚未填报，需要手动填报后，从**第二天开始**才能使用本脚本。



## 脚本依赖

- Python 3.6 或以上
- requests 库



## 脚本部署

本节以云服务器、AWS Lambda、GCP Cloud Function 为例阐述了部署的基本步骤，但本脚本也可以部署在其它的云函数平台上。欲知详情，请参考您的部署目标的文档。



#### 注意事项

- 如果您要自动运行本脚本，建议您于**每天上午 7:00** 运行；在 0 点运行可能会失败。



#### 部署在云服务器上

1. 通过 `git clone` 或 GitHub 的「下载 zip 文件」功能，将本仓库下载到您的电脑上。

2. 安装 Python 3.6 或以上版本。
   
3. `cd` 到脚本目录，通过 pip 安装依赖项：`pip install -r requirements.txt`。

4. 根据下方的「脚本配置与运行」一栏，配置脚本参数。

    

**注：** 如果您需要让该脚本定期自动运行：

1. Linux/macOS 用户可以配置 cron 等工具。参考教程：
   1. https://www.ibm.com/developerworks/cn/education/aix/au-usingcron/index.html
   2. https://crontab.guru/
2. Windows 用户可以使用系统的「任务计划」功能。



#### 部署在 AWS Lambda 上

由于 AWS Lambda 不会自动下载依赖项，因此需要您手动下载依赖项并打包上传。

1. 在 Linux 下配置 Python 3.6 虚拟环境，在虚拟环境中安装 requests。
2. 将虚拟环境下的 `site-packages` 文件夹中的内容，拷贝到与该脚本同一目录下。
3. 在 AWS Lambda 中新建一个函数：
   1. 按照下方「脚本配置与运行」一节的说明，配置环境变量。
   2. 将所有文件上传。
   3. 将要执行的文件设为 main.py，要执行的函数设为 main。

**注：** 您可以通过 AWS CloudWatch 来自动执行该脚本。



#### 部署在 GCP Cloud Function 上

GCP 支持通过 `requirements.txt` 自动下载依赖项，因此将所有文件（包括 `requirements.txt`） 打包上传即可。您需要：

1. 在 Cloud Function 中创建新函数。
   1. 按照下方「脚本配置与运行」一节的说明，配置环境变量。
   2. 打包上传本仓库所有文件。
   3. 将要执行的函数设为 main。

**注：** 建议您将该云函数的触发器设为 Cloud Pub/Sub 触发器，然后可以通过 GCP Cloud Scheduler 来自动执行该函数。



## 脚本配置与运行

该脚本需要配置北邮帐号等信息才能正确运行。

您可以通过**环境变量、命令行参数、修改代码**等方式来提供配置，请根据您部署的目标平台来决定使用哪种方式。

需要设置的参数如下：

| 环境变量      | 命令行参数      | 说明                                                         |
| :------------ | --------------- | :----------------------------------------------------------- |
| BUPT_SSO_USER | --bupt-sso-user | 您登录[北师大门户（https://one.bnu.edu.cn/）](https://one.bnu.edu.cn/)时使用的用户名，通常是您的学工号 |
| BUPT_SSO_PASS | --bupt-sso-pass | 您登录[北邮门户（https://one.bnu.edu.cn/）](https://one.bnu.edu.cn/)时使用的密码 |
| TG_BOT_TOKEN  | --tg-bot-token  | （可选）如果您需要把执行结果通过 Telegram 机器人告知，请将此变量设为您的 Telegram 机器人的 API Token |
| TG_CHAT_ID    | --tg-chat-id    | （可选）如果您需要把执行结果通过 Telegram 机器人告知，请将此变量设为您自己的用户 id |
| BNR_LOG_PATH  | --bnr-log-path  | （可选）日志文件存放的路径，未设置则不输出日志文件。（注意日志中可能有敏感信息） |

**注：** 优先级为：命令行参数 > 环境变量 > 代码中的默认值。其中前者覆盖后者。



#### 运行示例

假设您登录北邮门户的账户和密码是：

- **用户名：** 2020114514
- **密码：** 114514



#### 设置环境变量

您使用 Linux 时，可以通过如下 bash 命令，设置环境变量并运行脚本：

```bash
export BUPT_SSO_USER=2020114514
export BUPT_SSO_PASS=114514
python3 main.py
```

**注：** 

- 在 Windows 上，您使用的命令可能是 `python` 而不是 `python3`。您可以使用系统自带的「编辑环境变量」工具，也可以在使用 `cmd` 和 PowerShell 时设置环境变量。其中，`cmd` 和 PowerShell 的环境变量的语法各不相同，请自行研究。
- 各配置所对应的环境变量可查看上表。



#### 使用命令行参数

如果您认为设置环境变量，会让自己的密码有泄露风险，那么您可以使用环境变量提供用户名，同时又通过命令行参数来提供密码：

```bash
export BUPT_SSO_USER=2020114514
python3 main.py --bupt-sso-pass=114514
```

如果您觉得设置环境变量太麻烦，也可以全部使用命令行参数。

**注：** 各配置所对应的命令行参数可查看上表，也可以运行命令 `python main.py --help` 查看。



#### 修改代码（不推荐）

若您部署脚本的目标平台既不提供环境变量功能，也不允许设置命令行参数，那么您可以通过修改代码的方式提供配置。找到 CONFIG_SCHEMA 变量，给对应配置的 default 属性填入您的值即可。



## 配置代理以连接 Telegram 服务器

如果您在国内使用该脚本，您可能需要配置代理才能使用 Telegram 机器人通知功能。

本脚本所使用的 requests 库支持 HTTP 代理。您可以通过 Shadowsocks 工具开启 HTTP 代理后，将 HTTP_PROXY 和 HTTPS_PROXY 环境变量设为 `http://<代理 IP 地址>:<代理端口号>`。示例如下：

```bash
export HTTP_PROXY=http://127.0.0.1:1080
export HTTPS_PROXY=http://127.0.0.1:1080
```



## 版权

使用 MIT 协议发布，著作权由代码的贡献者所有。

