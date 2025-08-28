# 🫐Raspberry: A Better Launchpad

![w9zXSGp](https://i.imgur.com/w9zXSGp.png)

<p align="center">English | <a href="README_cn.md">简体中文</a></p>

<p align="center"><a href="https://t.me/+AODLypeF_aYwYjNh">Telegram</a> | <a href="https://twitter.com/ryanswindows">Twitter</a> | <a href="https://weibo.com/ryanthehitos">Weibo</a></p>

Raspberry is another macOS Launchpad alternative and even better to help you organize your groups on macOS Tahoe.

## Problems to Solve

Starting from macOS 26, Launchpad will become a completely new app called "Apps." From then on, the familiar interface of Launchpad will no longer be visible in the system. Although Apps has built-in software categories, it no longer supports custom grouping and categorization. This is undoubtedly negative news for users who need the original Launchpad interface and custom groups. Therefore, many people have created alternatives to Launchpad, with Raspberry being one of them, aiming to restore the basic functions of Launchpad while improving the user experience of some features. For example, compared to the original Launchpad, Raspberry provides a more flexible way of grouping through right-click, helping users efficiently organize and access applications, enhancing the desktop management experience.

## Functions

### Auto-save Group and Sort Settings (all versions), import existing Launchpad groups, migration made easier, no worries about backup and recovery (exclusive for paid users)

**Although many launcher software has manual grouping features, for users transferring from previous generations of macOS, migrating existing group information is a big headache.**

Pay attention to the changes in the background in the following demonstration, where most of the software has almost instantly found their original combinations:

https://github.com/user-attachments/assets/48e4dd4a-f630-4f49-9d56-ee80bacad3e1

Raspberry focuses on this feature. As the author of Raspberry, I have over 700 software and 21 groups on my Mac. If I had to regroup each software again, what a massive project that would be! (Not to mention that before, Launchpad required dragging to group, which was even more difficult.)

Therefore, Raspberry has added a migration feature in the paid version, which can save the user's Launchpad groups on the system before macOS 26 locally, and then restore them with one click after the user upgrades to macOS 26. (Note: **This feature requires purchasing and installing Raspberry's paid version before the upgrade and operating it correctly**.)

In addition, users can save their current grouping structure at any time, and can also return to any previous archive point at any time:

https://github.com/user-attachments/assets/030cad24-007d-4323-98c9-90f302cabd41

### First launch automatically indexes all applications, supports automatic updates for new applications

During the first launch, the Raspberry icon will flicker in the Dock bar for a while, which is a normal phenomenon because it is indexing the apps on the computer. This indexing is not based on Spotlight, so even if the system is updated, the index is saved locally and will not be lost. 

After the indexing is completed, the first time you open the main interface will look like this:

https://github.com/user-attachments/assets/6097778f-b5f9-4b0a-8b89-98c0152532d1

### One-click Application Launch, Smooth Operation

Like all startup software, a left-click on the icon of a certain software will open and run that software. If a group is clicked, the group will be opened.

In addition to clicking, Raspberry has also added the double-click method, which can be used to exit the interface, rename by double-clicking, and so on.

https://github.com/user-attachments/assets/efa1de8d-48ad-4aec-996f-f4d6dcd7bbd3

### Right-click to group, add, remove, and rename applications, group management is efficient and convenient

In addition to the basic functions of the left-click, Raspberry has added right-click functionality to the native Launchpad, allowing for the creation of groups for a software, joining groups, moving from one group to another, returning to the main interface, and moving to the trash can.

https://github.com/user-attachments/assets/db7b64ef-cf7a-4388-8944-2e09988c282e

### Eight shortcut keys for quick operation and sorting, enhancing efficiency

1. **Space key: Focus and move the focus to the right**

https://github.com/user-attachments/assets/1f9132fe-fadc-4546-ba25-61e39bf4abf5

The space key is to focus on the first software icon on the current interface when there is no focus (if the focus is on the search bar, the effect is to enter a space in the search bar, so you need to click the main interface first to deselect the search bar at this time), and when the software icon is currently focused, to move the focus right and down. There will be a blue border around the software when focused.

2. **Shift+Space key: move focus to the left**

https://github.com/user-attachments/assets/51c203c0-aabb-492f-b1c2-c2e58c7354a3

If the Shift+Space key is pressed, the effect is opposite to that of the Space key moving the focus to the right; the focus will move to the left.

3. **Left and Right Keys: Page Flip**

https://github.com/user-attachments/assets/7813bd5f-c71b-4171-aa5d-3e5075128d69

The left and right keys on the keyboard can be used to flip pages left and right in the Raspberry, whether it's on the main interface or within a group.

4. **Shift+Left/Right arrow keys: Swap positions of icons on the left and right**

https://github.com/user-attachments/assets/88fe9d73-cb61-4089-a64d-d3f4c5e2b703

If Shift+Left/Right arrow keys are pressed while there is a focus on the current item, the current software icon or group will swap positions with the icon on the left or right side. This can be pressed continuously. It is suitable for customizing the order of software icons.

5. **Up and down arrow keys: Move focus up and down**

https://github.com/user-attachments/assets/d3466a4f-16c7-42a4-a476-dfe829f9c823

If you want to move the focus to a specific line, in addition to using the space bar continuously, you can also use the up and down arrow keys to move the focus more efficiently. The space bar always moves the focus to the right, so it takes eight presses to move to the second line. The up and down arrow keys move the focus between icons in the same column of the two lines above and below, allowing you to switch lines with just one press.

6. **Enter key: Open software and open group (left-click)**

https://github.com/user-attachments/assets/169274b2-dbaa-40f4-b3ae-cde79a0ef8fb

When the focus appears, pressing the Enter key is equivalent to left-clicking on the software or group under the focus, which will open this software or open this group.

7. **Shift+Enter key: Open right-click options (right-click)**

https://github.com/user-attachments/assets/09f8772c-4bd4-4e84-bc49-a8d5e2106320

Corresponding to the left-click effect of the Enter key, if the Enter key is pressed while the Shift key is pressed, it is equivalent to right-clicking on the software or group under the current focus.

8. **Tab key to exit group**

https://github.com/user-attachments/assets/e783b225-b88b-4d3e-8642-3202b0f5c1cd

After opening a group, pressing the Tab key can close the current group and return to the main interface.

### Removed Drag-and-Drop from Native Launchpad

In the native Launchpad, users could combine two software icons by dragging them together to form a group. Raspberry prefers the right-click method, so this feature is no longer added. Additionally, the native Launchpad can only add groups through dragging, so when a user drags a software into a group at the end of a row, it becomes a classic cat-and-mouse chase game. Moreover, manually dragging hundreds of software from multiple pages to a specific group on the first page is very energy-consuming and not a simple design.

At the same time, Raspberry has also removed the feature of changing software order through dragging, replacing it with shortcut keys, which will greatly enhance stability. The situation of dragging a software from a very late page to the front through a dragging gesture will no longer occur.

### Increased the Dots on Native Launchpad for Easier Mouse Clicking

In the native Launchpad, the dots below the pages can also be clicked to jump between them, but unfortunately, they are too small and not easy to click. Raspberry has made these dots larger and easier to click when replicating, making it convenient for users to use either the mouse or shortcut keys.

## Interface

Raspberry has a simple and beautiful interface design, with grouping clear at a glance and smooth operation. Grouping and application icons are presented clearly, supporting quick search and switching.

Main Interface:

![fDQMlMu](https://i.imgur.com/fDQMlMu.jpeg)

Group interface:

![4jWmZEt](https://i.imgur.com/4jWmZEt.jpeg)

"Actions" option in the menu bar:

![VUsWFd1](https://i.imgur.com/VUsWFd1.png)

"About" option in the menu bar:

![DmbQqdR](https://i.imgur.com/DmbQqdR.png)

"Language" option in the menu bar

![mjMMKoR](https://i.imgur.com/mjMMKoR.png)

## Environment Requirements

- Operating System: macOS 15 and above versions
- Chip: M series chip

## Pricing

The free version only includes basic features, while the paid version, in addition to the basic features, also has advanced features.

| | Free Version | Paid Version |
|------|---------------------------------------------|---------------------------------------------|
| Basic Features | 1. Index all applications, supports automatic update of new applications<br>2. Launch applications<br>3. Right-click to group, add, remove, and rename applications<br>4. Use shortcuts for quick operations and sorting | 1. Index all applications, supports automatic update of new applications<br>2. Launch applications<br>3. Right-click to group, add, remove, and rename applications<br>4. Use shortcuts for quick operations and sorting|
| Advanced Features | None | 5. Import existing Launchpad groups<br>6. Manually backup and restore current groups<br>7. Multiple languages other than English|
| Price | Free | $3 (before 0:00 on September 1, 2025 in Tokyo time)<br>Thereafter will be $5|
| Obtain | [Github Releases](https://github.com/Ryan-the-hito/Raspberry/releases) | [Click to Buy](https://buymeacoffee.com/ryanthehito/e/451635) |

Purchase and Payment Instructions:

To purchase this software, please follow the instructions below:

1. Visit the (Buy me a coffee link)[https://www.buymeacoffee.com/ryanthehito/e/155171].
2. Fill in your name and email address in the provided fields.
3. Choose your preferred payment method: bank card or link.
4. Complete the payment process.
5. Upon successful payment, you will receive the Pro version software package.
6. The software package can be installed on multiple devices.

Thank you for your support and recognition of open-source paid software. As an independent developer, I deeply appreciate the encouragement from all supporters.

<p align="center">
  <img src="https://i.imgur.com/cMrTPxi.png" width=400 />
  <img src="https://i.imgur.com/xdsznlL.png" width=400 />
</p>

## Installation

1. Go to the [GitHub repository](https://github.com/Ryan-the-hito/Raspberry) to download the latest version;
2. Unzip the installation package, open the dmg file, and drag the app within it into the corresponding folder;
3. **It is recommended to go to System Settings before running and grant Raspberry auxiliary function permissions under the Security & Privacy section. If a prompt asking for AppleEvent permissions appears, please allow it;**
4. Run the main program, wait for the indexing to complete on the first launch, and it can be used.

## Instructions for use

This software does not have a settings interface. If you need instructions within the software, you can go to the "About" menu bar, where you can see the guide window button, which includes a quick guide.

1. Start the Raspberry application. **On the first launch, it will bounce several times in the dock, which is a normal phenomenon. Please do not manually close it. The bouncing duration depends on the number of software, and it can last up to several minutes. Please be patient. This phenomenon will not occur after normal use.**

https://github.com/user-attachments/assets/1208f7f0-fa26-450b-a956-e17cc62c03d1

Since the loading of the main interface elements of the software must be completed in the main thread, it is not possible to silently establish an index in the background. However, as long as it is used normally, the established index will not disappear for no reason, so this situation will not occur again thereafter.

2. Note: **Double-clicking different areas corresponds to different functional effects:**

<p align="center">
<img src="https://i.imgur.com/udvmycy.png" width=600 />
</p>

3. If you click an option to let Raspberry clear the cache and re-index, do not click this button repeatedly and do not exit the application before the cache is completed.

## Notice

- If the startup option is enabled, it is necessary to uncheck "Open the last opened window at startup" when shutting down, as this may cause two Raspberry windows to open simultaneously when the computer starts up next time.
- Please back up the group data regularly to prevent accidental loss.

## Q&A

If you encounter any special situations, please visit **[Q&A](https://github.com/Ryan-the-hito/Q-A)❓** to see if there is a ready-made solution, or further [contact me](sweeter.02.implant@icloud.com).

## License

This project is licensed under the GPL-3.0 open source license; for details, please refer to the LICENSE file.

## Credit

1. [Qt](https://github.com/qt): This software follows the open-source protocol of Qt;

2. [blacktop/lporg: Organize Your macOS Launchpad Apps](https://github.com/blacktop/lporg): This software benefits from this MIT licensed project.

Thank you all for the support and suggestions from the open-source community.

## Sponsor me

If you like Raspberry, please click Star or submit an Issue. You can also follow the author on GitHub to support the continuous update of the project.

[![D4KakEu](https://i.imgur.com/D4KakEu.png)](https://www.buymeacoffee.com/ryanthehito)

<p align="center">
  <img src="https://i.imgur.com/OHHJD4y.png" width=240 />
  <img src="https://i.imgur.com/6XiKMAK.png" width=240 />
</p>

## To-dos

- [x] Multilingual

- [x] Backup group and restore backup

- [x] Menu background color bug under dark theme

- [x] Animation effect after search box focus

- [x] Add border effect to groups

- [x] Automatic size detection for multi-screen

- [x] Rename bug on the main interface

- [x] Do not start another Raspberry if one is already running (exit the other)

- [x] Shortcut key to close the main interface

## Versions

### v0.0.8

- Fixed a bug in Pro version that is not displaying the right version number.
- Added a shortcut key to close the main interface

### v0.0.7

Added Japanese UI interface.

### v0.0.6

Added Chinese UI interface.

### v0.0.5

Bug fixes in v0.0.5:

- Resolved an issue when using multiple displays will result in unadjustable sizes;
- Fixed a bug that it could be launched twice.

### v0.0.4

Bug fixes in v0.0.4:

- Resolved a bug when dark theme cannot be implemented for pop-up warning windows;
- Fixed the renaming bug in the right-click menu;
- Fixed the bug when clicking the blank areas in the main window cannot trigger closing actions;
- Added new feature to backup and restoring backups for paid version.

### v0.0.3

Bug fixes and new animations in v0.0.3:

- Fixed a bug when menu shows wrong color under dark theme;
- Added animation for the search bar when under focus;
- Added glass-like widget for groups;
- All the icons are now top aligned when displayed;
- Added animation when changing pages.

### v0.0.2

Bug fixes.

### v 0.0.1

The very initial release. 
