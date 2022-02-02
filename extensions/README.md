## Overview 

Script to create extension for Google Chrome and Mozilla Firefox.

## How to use

1. Insert script file into folder with plugin and run it.
2. Find folder with extension in plugin's folder.

## How to install
* For browser Chrome: Go to settings -> extensions -> enable developer mode -> download the unpacked extension -> find plugin in plugins tab in onlyoffice editor.
* For browser Mozilla there are two ways to install extension: 
1. 
   1. Put the contents of the folder with the extension into a zip archive. 
   2. Go to settings -> extensions -> at the item *manage my extensions* click on the nut -> install the add-on from the file -> select the archive with the extension -> find     plugin in plugins tab in onlyoffice editor.
2. Enter in the address bar **about:debugging** -> This Firefox -> download temporary add-on -> select **manifest.json** file in folder with extension -> find plugin in plugins tab in onlyoffice editor.
### Note
Starting with Firefox 43 all add-ons must be signed before they can be installed in the browser. You can only remove this restriction in [Firefox Developer Edition](https://www.mozilla.org/en-US/firefox/developer/) or [Firefox Nightly](https://nightly.mozilla.org/) with the following steps: 
- Go to the about:config page in Firefox
- Use the search bar to find xpinstall.signatures.required
- Double click on this property or use the local menu (right click) to select "Toggle" to set it to false.
