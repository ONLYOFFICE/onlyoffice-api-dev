#!/usr/bin/env python
import shutil
import uuid
import json
import os
import io
import sys
from os import listdir
from os.path import isfile, join

if (sys.version_info[0] >= 3):
    unicode = str


def readFile(path):
    if os.path.exists(path):
        with io.open(path, "r", encoding="utf-8") as file:
            filedata = file.readlines()
        return filedata
    return ''


def writeFile(path, content):
    if (os.path.isfile(path)):
        os.remove(path)

    with io.open(path, "w", encoding="utf-8") as file:
        file.write(unicode(content))
    return


# all files
list_of_files = []
for root, dirs, files in os.walk('./'):
    if -1 != root.find('./.git'):
        continue
    for file in files:
        if -1 == file.find('.md') and -1 == file.find('.txt') and -1 == file.lower().find('.license') and -1 == file.lower().find('license') and file.lower().find('create_extanstion.py'):
         list_of_files.append('"/plugin/' + os.path.join(root, file).replace('./', '').replace('\\', '/') + '"')

# get plugin name
pluginName = ''
arrConfigString = readFile('config.json')
for line in arrConfigString:
    if -1 != line.find('"name"'):
        pluginName = line.split(':')[1].replace('"', '').replace(' ', '').replace(',', '').replace('\n', '')

# resources
web_accessible_resources = ''
for file in list_of_files:
  if file != os.path.basename(__file__) and file != 'README.md':
    web_accessible_resources += '\t\t\t\t' + file + ',\n'
web_accessible_resources +='\t\t\t\t"/main.js"\n'

# content security policy
content_security_policy = ''
html_lines = readFile('index.html')
for line in html_lines:
  if -1 != line.find('src="https:'):
      content_security_policy += line.split('src="')[1].replace('"></script>', '').replace('\n', '') + ' '
main_js = '/**\n\
 *\n\
 * (c) Copyright Ascensio System SIA 2020\n\
 *\n\
 * Licensed under the Apache License, Version 2.0 (the "License");\n\
 * you may not use this file except in compliance with the License.\n\
 * You may obtain a copy of the License at\n\
 *\n\
 *     http://www.apache.org/licenses/LICENSE-2.0\n\
 *\n\
 * Unless required by applicable law or agreed to in writing, software\n\
 * distributed under the License is distributed on an "AS IS" BASIS,\n\
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n\
 * See the License for the specific language governing permissions and\n\
 * limitations under the License.\n\
 *\n\
 */\n\
(function(window, undefined){\n\
\n\
	if ("frameEditor" == window.name)\n\
	{\n\
		var _url = chrome.extension.getURL("main.js");\n\
		_url = _url.substr(0, _url.lastIndexOf("main.js"));\n\
\n\
		var _baseUrl = _url + "plugin/";\n\
		var _configUrl = _baseUrl + "config.json";\n\
\n\
		function onLoadConfig(_json)\n\
		{\n\
			var _obj = _json;\n\
			_obj.baseUrl = _baseUrl;\n\
\n\
			var _obj_value = JSON.stringify(_obj);\n\
			_obj_value = _obj_value.replace(/\"/g, ' + r"'\\\"'" + ');\n\
\n\
			var _script_content = "' + r'\
            (function(window, undefined) {\n\
				var _value = JSON.parse(\"" + _obj_value + "\");\
				window.Asc = window.Asc ? window.Asc : {};\n\
				window.Asc.extensionPlugins = window.Asc.extensionPlugins ? window.Asc.extensionPlugins : [];\n\
				window.Asc.extensionPlugins.push(_value);\n\
				\n\
				if (window.Asc.g_asc_plugins)\n\
				{\n\
					window.Asc.g_asc_plugins.loadExtensionPlugins(window.Asc.extensionPlugins);\n\
					window.Asc.extensionPlugins = [];\n\
				}\n\
			})(window, undefined);";' + '\n\
			var _script = document.createElement("script");\n\
			_script.appendChild(document.createTextNode(_script_content));\n\
			(document.body || document.head || document.documentElement).appendChild(_script);\n\
		}\n\
\n\
		var xhr = new XMLHttpRequest();\n\
		xhr.open("GET", _configUrl, true);\n\
		xhr.responseType = "json";\n\
		xhr.onload = function()\n\
		{\n\
			if (this.status === 200)\n\
			{\n\
				onLoadConfig(xhr.response);\n\
			}\n\
		};\n\
		xhr.send();\n\
	}\n\
})(window, undefined);'

manifest = '{\n\
	"name": "' + pluginName + '",\n\
	"description": "Plugin for ONLYOFFICE. ' + pluginName + '",\n\
	"version": "1.0",\n\
	"manifest_version": 2,\n\
	"background": {\n\
	},\n\
	"browser_action": {\n\
		"default_icon": {\n\
			"19": "./plugin/resources/light/icon.png",\n\
			"38": "./plugin/resources/light/icon@2x.png"\n\
		}\n\
	},	\n\
	"web_accessible_resources": [\n' + web_accessible_resources + '	],\n\
	"content_scripts": [\n\
	{\n\
		"match_about_blank" : true,\n\
		"all_frames" : true,\n\
		"matches": ["<all_urls>"],\n\
		"js": [ "/main.js" ],\n\
		"run_at": "document_end"\n\
	}\n\
	],\n\
	"permissions": [\n\
		"file:///*",\n\
		"<all_urls>",\n\
		"tabs"\n\
	],\n\
	"content_security_policy": "script-src ' + "'self'" + ' ' + content_security_policy + ' ' + "'unsafe-eval'" + '; object-src ' + "'self'" + '"\n\
}'

def ignore_most(folder, names):
  ignore_list = []
  for name in names:
    if -1 != name.find('.git') or -1 != name.find('create_extension.py'):
      ignore_list.append(name)
  return ignore_list

folder_with_ext = 'extension-dist'
if True == os.path.isdir('./' + folder_with_ext):
  shutil.rmtree('./' + folder_with_ext, ignore_errors=True)
shutil.copytree('./', './' + folder_with_ext + '/plugin/', ignore=ignore_most)

writeFile('./' + folder_with_ext + '/main.js', main_js)
writeFile('./' + folder_with_ext + '/manifest.json', manifest)