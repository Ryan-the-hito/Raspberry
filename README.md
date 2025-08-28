# 🫐Raspberry: A Better Launchpad

![w9zXSGp](https://i.imgur.com/w9zXSGp.png)

<p align="center"><a href="README.md">English</a> | 简体中文</p>

<p align="center"><a href="https://t.me/+AODLypeF_aYwYjNh">Telegram</a> | <a href="https://twitter.com/ryanswindows">Twitter</a> | <a href="https://weibo.com/ryanthehitos">Weibo</a></p>

Raspberry is another macOS Launchpad alternative and even better to help you organize your groups on macOS Tahoe.

## 解决问题

从 macOS 26 起，Launchpad 将变为一个全新的 app——Apps。自此之后，Launchpad 的熟悉界面将再也无法在系统中看到了。虽然 Apps 中有自带的软件分类，但却无法再支持自定义分组分类。对于需要 Launchpad 原生界面以及自定义分组的用户来说，这无疑是一个负面消息。因此，有很多人制作了 Launchpad 的替代品，Raspberry 也是其中之一，旨在还原 Launchpad 的基本功能的同时，弥补甚至提升部分功能的使用体验。例如，相比原生 Launchpad，Raspberry 通过右键方式提供更灵活的分组方式，帮助用户高效整理和访问应用，提升桌面管理体验。

## 功能亮点

### 自动保存分组和排序设置（所有版本），导入原有 Launchpad 分组，迁移更省心，备份恢复不用愁（付费专享）

**虽然许多启动器软件都具有手动分组功能，但对于从前代 macOS 转移过来的用户来说，迁移现有的分组信息才是大麻烦。**

注意看下面演示中背景发生的变化，几乎在一瞬间，大部分的软件找回了自己原有的组合：

https://github.com/user-attachments/assets/48e4dd4a-f630-4f49-9d56-ee80bacad3e1

Raspberry 主打这项功能。作为 Raspberry 的作者，我的 Mac 上有超过 700 个软件和 21 个分组，如果要一个一个软件再分组一次，这得是多大的工程！（更别提以前 Launchpad 需要拖拽才能分组，更困难了）

因此，Raspberry 在付费版中增加了迁移功能，可以将用户在 macOS 26 之前系统上的 Launchpad 分组保存在本地，待用户升级到 macOS 26 之后，再一键恢复。（需要注意的是：**此功能需要在升级前就购买并安装 Raspberry 的付费版并正确操作**）

此外，用户还可随时保存自己当前的分组结构，亦可在任何时候回复到之前的存档点：

https://github.com/user-attachments/assets/030cad24-007d-4323-98c9-90f302cabd41

### 首次启动自动索引所有应用，支持自动更新新应用

首次启动时，Raspberry 的图标会在 Dock 栏中跳动多时，这是正常现象，因为它正在索引电脑中的 app，这个索引不基于 Spotlight，因此即便更新系统，也保存在本地不丢失。

索引完成之后，首次打开主界面是这样的：

https://github.com/user-attachments/assets/6097778f-b5f9-4b0a-8b89-98c0152532d1

### 一键启动应用，操作流畅

如所有启动软件一样，左键单击某一个软件的图标，即可打开运行这个软件。如果单击的是分组，那么就会打开这个分组。

除单击外，Raspberry 还增加了双击的方法，可以通过双击退出界面、双击重命名等。

https://github.com/user-attachments/assets/efa1de8d-48ad-4aec-996f-f4d6dcd7bbd3

### 右键分组、添加、移除、重命名应用，分组管理高效便捷

除了左键的基本功能外，Raspberry 在原生 Launchpad 的基础上增加了右键功能，可以为一个软件创建分组、加入分组、从一个分组移动到另一个分组、移回主界面以及移动到垃圾篓。

https://github.com/user-attachments/assets/db7b64ef-cf7a-4388-8944-2e09988c282e

### 八大快捷键快速操作与排序，提升效率

1. **空格键：聚焦与向右移动焦点**

https://github.com/user-attachments/assets/1f9132fe-fadc-4546-ba25-61e39bf4abf5

空格键的效果是在没有聚焦的时候聚焦到当前界面上的第一个软件图标（如果聚焦在了搜索栏上，那么效果就是在搜索栏里键入空格了，因此此时需要先单击一下主界面取消选中搜索栏），并在当前聚焦了软件图标的时候，向右向下移动聚焦的软件。聚焦时软件周围会有一个蓝色边框。

2. **Shift+空格键：向左移动焦点**

https://github.com/user-attachments/assets/51c203c0-aabb-492f-b1c2-c2e58c7354a3

如果按下 Shift+空格键，那么与空格键向右移动焦点的效果相反，焦点将向左移动。

3. **左右键：翻页**

https://github.com/user-attachments/assets/7813bd5f-c71b-4171-aa5d-3e5075128d69

键盘上的左右键可以用来在 Raspberry 里左右翻页，不管是在主界面上还是在分组内均是如此。

4. **Shift+左右键：左右更换排序**

https://github.com/user-attachments/assets/88fe9d73-cb61-4089-a64d-d3f4c5e2b703

如果在当前**有聚焦**的前提下按下 Shift+左右键，那么当前的软件图标或是分组会和左或右侧的图标相互更换位置，可以连续按。适用于给软件自定义排序的情形。

5. **上下键：上下行移动焦点**

https://github.com/user-attachments/assets/d3466a4f-16c7-42a4-a476-dfe829f9c823

如果想将焦点移动到某一行，除了连续使用空格键，还可以使用上下键移动焦点，更有效率。空格键始终向右移动焦点，因此移动到第二行需要按八次左右。而上下键在上下两行之间的同一列图标间移动焦点，只需一次即可将焦点换行。

6. **回车键：打开软件与打开分组（左键单击）**

https://github.com/user-attachments/assets/169274b2-dbaa-40f4-b3ae-cde79a0ef8fb

当焦点出现的时候按下回车键，就相当于左键单击这个焦点下的软件或者分组，这将打开这个软件或者打开这个分组。

7. **Shift+回车键：打开右键选项（右键单击）**

https://github.com/user-attachments/assets/09f8772c-4bd4-4e84-bc49-a8d5e2106320

与回车键的左键单击效果对应，如果在 Shift 键按下的情况下按下回车，那么就相当于右键单击当前焦点下的软件或者分组。

8. **Tab 键退出分组**

https://github.com/user-attachments/assets/e783b225-b88b-4d3e-8642-3202b0f5c1cd

当打开一个分组后，按下 Tab 键可以关闭当前分组并回到主界面。

### 从原生 Launchpad 中去除了拖拽

在原生的 Launchpad 中，用户可以通过拖拽的方式，将两个软件的图标组合在一起，形成一个组别，Raspberry 倾向于使用右键的方式，因此不再添加这个功能。另外，原生的 Launchpad 因为只能通过拖拽添加组别，因此当用户将一个软件拖拽加入位于行尾的组别中时，会变成经典的猫鼠追逐游戏。此外，让用户手动将上百个软件从多页之后手动拖拽到第一页的指定组别中，非常耗费精力，不是简洁的设计。

同时，Raspberry 也去除了通过拖拽来改变软件顺序的功能，取而代之的是使用快捷键，这会极大地增添稳定性，以前通过拖拽手势，把一个软件从很后面的页面里拽到前面的事情不会再发生了。

### 增大了原生 Launchpad 的圆点，便于鼠标点击

在原生 Launchpad 中，页面下方的圆点也是可以点击并用来跳转的，但可惜的是尺寸太小，不便于点击。Raspberry 在复刻的时候把这些圆点做得更大、便于点击，无论用户习惯用鼠标还是快捷键，都能很方便地使用。

## 界面一览

Raspberry 拥有简洁美观的界面设计，分组一目了然，操作流畅。分组与应用图标清晰呈现，支持快速查找和切换。

主界面：

![fDQMlMu](https://i.imgur.com/fDQMlMu.jpeg)

分组界面：

![4jWmZEt](https://i.imgur.com/4jWmZEt.jpeg)

菜单栏“操作”选项：

![VUsWFd1](https://i.imgur.com/VUsWFd1.png)

菜单栏“关于”选项：

![DmbQqdR](https://i.imgur.com/DmbQqdR.png)

菜单栏“语言”选项

![mjMMKoR](https://i.imgur.com/mjMMKoR.png)

## 环境要求

- 操作系统：macOS 15 及以上版本
- 芯片为 M 系列芯片

## 类型价目

免费版只有基本功能，付费版在基本功能之外，还拥有高级功能。

|      | 免费版                      | 付费版                      |
|------|-----------------------------|-----------------------------|
| 基本功能 |1. 索引所有应用，支持自动更新新应用<br>2. 启动应用<br>3. 右键分组、添加、移除、重命名应用<br>4. 快捷键快速操作与排序 | 1. 索引所有应用，支持自动更新新应用<br>2. 启动应用<br>3. 右键分组、添加、移除、重命名应用<br>4. 快捷键快速操作与排序|
| 高级功能 | 无 | 5. 导入原有 Launchpad 分组<br>6. 手动备份当前分组并恢复|
| 价格 | 免费                        | $3 （2025 年 9 月 1 日 0 时前），此后将变为 $5    |
| 获取 | [Github Releases](https://github.com/Ryan-the-hito/Raspberry/releases)  | [点击购买](https://www.buymeacoffee.com/ryanthehito) |

购买与支付说明：

本软件将通过 Buy me a coffee 销售，以下为订购界面示意图，购买者需提供称呼和邮箱地址，并通过银行卡或 link 付款，支付一次即获得 Pro 版软件包，可多安装于多个设备。作为独立开发者，我由衷地感谢所有支持者对开源付费软件的支持和认可。

<p align="center">
  <img src="https://i.imgur.com/cMrTPxi.png" width=400 />
  <img src="https://i.imgur.com/xdsznlL.png" width=400 />
</p>

## 下载安装

1. 前往 [GitHub 仓库](https://github.com/Ryan-the-hito/Raspberry) 下载最新版本；
2. 解压安装包，打开 dmg 文件，按指示将其中的 app 拖入对应文件夹；
3. **建议在运行前前往系统设置，在安全与隐私栏目授予 Raspberry 辅助功能权限。若弹出提示请求 AppleEvent 权限，请允许；**
3. 运行主程序，首次启动需等待其索引完成，即可使用。

## 使用说明

本软件并无设置界面，如果在软件内部需要使用说明，可以前往“关于”菜单栏，即可看到指南窗口按钮，内附一份快速引导。

1. 启动 Raspberry 应用，**初次启动会在程序坞中弹跳数次，这是正常现象，请勿人为关闭。弹跳时长视软件数量而定，长可达十数分钟，请耐心等待。**

https://github.com/user-attachments/assets/1208f7f0-fa26-450b-a956-e17cc62c03d1

2. 需注意：**双击不同区域对应不同功能效果：**

<p align="center">
  <img src="https://i.imgur.com/ASvXDsJ.png" width=600 />
</p>

## 注意事项

- 如果开启了开机自启选项，那么需要在关机的时候取消选择“在开机的时候打开上次打开的窗口”，因为这可能导致下次开机时同时打开两个 Raspberry 窗口。
- 请定期备份分组数据，防止意外丢失。

## Q&A

如果遇到任何特殊情况，请访问 **[Q&A](https://github.com/Ryan-the-hito/Q-A)❓** 查看是否有现成的解决方案，或进一步[联系我](sweeter.02.implant@icloud.com)。

## 证书信息

本项目采用 GPL-3.0 开源许可证，详情请查阅 LICENSE 文件。

## 特别致谢

1. [Qt](https://github.com/qt)：本软件遵循 Qt 的开源协议；
2. [blacktop/lporg: Organize Your macOS Launchpad Apps](https://github.com/blacktop/lporg): 本软件受惠于此 MIT 证书项目。
感谢所有开源社区成员的支持与建议。

## 支持作者

如果你喜欢 Raspberry，欢迎点 Star 或提交 Issue。也可通过 GitHub 关注作者，支持项目持续更新。

[Buy Me a Cup of Coffee](https://www.buymeacoffee.com/ryanthehito)

<p align="center">
  <img src="https://i.imgur.com/OHHJD4y.png" width=240 />
  <img src="https://i.imgur.com/6XiKMAK.png" width=240 />
</p>

## 待办功能

[x] 多语言
[x] 备份 group 和恢复备份
[x] 暗色主题下菜单背景颜色 bug
[x] 搜索框聚焦后动画效果
[x] 加上分组的边框效果
[x] 多屏幕自动检测尺寸
[x] 主界面上重命名 bug
[x] 如果已经有一个 Raspberry 在运行，就不要启动另一个（退出另一个）
[ ] 关闭主界面的快捷键

## 版本历史
