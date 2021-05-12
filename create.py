#!/usr/bin/env python
import shutil
import uuid
import json
import os
import re
import base64

def readFile(path):
  if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as file:
      filedata = file.read()
    return filedata
  return ''

def writeFile(path, content):
  if (os.path.isfile(path)):
    os.remove(path)

  with open(path, "w", encoding="utf-8") as file:
    file.write(content)
  return

class EditorApi(object):
  def __init__(self):
    self.records = []
    self.init = False
    self.folder = "word"
    self.type = "CDE"
    self.numfile = 0
    self.files = []
    self.typedefParams = []
    self.methodsRetuns = []
    return

  def initFiles(self, type, files):
    self.folder = type
    if "word" == self.folder:
      self.type = "CDE"
    elif "slide" == self.folder:
      self.type = "CPE"
    else:
      self.type = "CSE"
    self.files = files
    return

  def getAlias(self, description):
    value = re.search(r'@alias.+', description)
    if (None != value):
      return value.group().strip().split(' ')[1]
    return ''

  def getReturnValue(self, description):
    paramStart = description.find("@returns {")
    if -1 == paramStart:
      return "{}"
    paramEnd = description.find("}", paramStart)
    retParam = description[paramStart + 10:paramEnd]
    isArray = False
    if -1 != retParam.find("[]"):
      isArray = True
      retParam = retParam.replace("[]", "")
    retType = retParam.replace("|", " ").split(" ")[0]
    retTypeLower = retType.lower()
    retValue = ""
    if -1 != retType.find("\""):
      retValue = "\"\""
    elif "bool" == retTypeLower:
      retValue = "true"
    elif "string" == retTypeLower:
      retValue = "\"\""
    elif "number" == retTypeLower:
      retValue = "0"
    elif "undefined" == retTypeLower:
      retValue = "undefined"
    elif "null" == retTypeLower:
      retValue = "null"
    else:
      retValue = "new " + retType + "()"
    if isArray:
      retValue = "[" + retValue + "]"
    return "{ return " + retValue + "; }"
  def compareComplexParams(self, complexParams):
    for nParamForCheck in range(len(complexParams) - 1, -1, -1):
      for nParamMain in range(len(complexParams) - 1, -1, -1):
        if nParamMain == nParamForCheck or len(complexParams) == 1:
          continue
        sParamNameForCheck = complexParams[nParamForCheck]["sName"]
        sParamName = complexParams[nParamMain]["sName"]

        if 0 == sParamNameForCheck.find(sParamName) and len(sParamNameForCheck.split(sParamName + '.')[1].split('.')) == 1:
          complexParams[nParamMain]["sType"][sParamNameForCheck.split(sParamName + '.')[1]] = complexParams[nParamForCheck]["sType"]
          del complexParams[nParamForCheck]
          nParamForCheck -= 1
          nParamMain -= 1
    for nParam in range(len(complexParams)):
      complexParams[nParam]['sType'] = json.dumps(complexParams[nParam]['sType']).replace('"','')
    return complexParams

  def get_typedef_param(self, sParamName):
    for param in self.typedefParams:
      if sParamName == param['sName']:
        #return json.dumps(param['sType']).replace('"','') if type(param['sType']) is dict else param['sType']
        return self.getDictAsObject(param['sType']) if type(param['sType']) is dict else param['sType']
        #return param['sType']
    return ''
  def getParamNameFromLine(self, sLine):
    return sLine.split(re.search('{+.+} ', sLine).group())[1].strip().split(' ')[0].split('=')[0].replace('\n','').replace('[','').replace(']','')
  def getParamTypeFromLine(self, sLine):
    line = sLine.replace('\n', ' ')
    matches = re.search(r'{+.+} ', line).group()
    return matches[0:matches.find('} ') + 1].replace('?', '').strip().replace('(', '').replace(')', '').replace('{', '').replace('}', '').strip()
  def getParams(self, desсription):
    allParams = []
    complexParams = []

    isAlreadyAdded = False
    records = desсription.split('@param')
    if 0 != len(records):
      records = records[1:]
    for nRecord in range(len(records)):
      isAlreadyAdded = False
      paramName = self.getParamNameFromLine(records[nRecord])
      paramType = self.getParamTypeFromLine(records[nRecord])
      if True == self.is_typedef_param('{' + paramType.replace('[','').replace(']','').replace('?', '') + '}'):
        paramType = self.get_typedef_param(paramType.replace('[','').replace(']','').replace('?', '').replace('{', '').replace('}',''))
      for nParam in range(len(complexParams)):
        complexParamName = complexParams[nParam]["sName"]
        if 0 == paramName.find(complexParamName) and -1 == paramType.lower().find('object'):
          trueParamName = paramName.split(complexParamName + '.')[1]
          if (len(trueParamName.split('.')) == 1):
            complexParams[nParam]["sType"][trueParamName] = paramType
            isAlreadyAdded = True
      if type(paramType) is not dict and -1 != paramType.lower().find('object'):
        complexParams.append({"sName": paramName, "sType": {}})
      elif False == isAlreadyAdded:
        allParams.append({"sName": paramName, "sType": paramType})
    complexParams = self.compareComplexParams(complexParams)
    return allParams + complexParams

  def createMethodInterface(self, sAlias, arrParams, returnValue):
    sResultDescription = '\texecuteMethod(name: "' + sAlias + '", args: ['
    for nParam in range(len(arrParams)):
      paramType = arrParams[nParam]['sType']
      if type(paramType) is dict:
        for key in paramType:
          sResultDescription += key + ': ' + paramType[key] + ', '
      else:
        sResultDescription += arrParams[nParam]['sName'] + ': ' + paramType.replace('?','') + ', '
    sResultDescription = sResultDescription.rstrip(', ') + ']'
    if "" != returnValue:
      sResultDescription += ', callbackfn: (argument : typeof ' + sAlias + ') => void) : ' + returnValue + ';'
    return sResultDescription

  def add_all_typedef_params(self, recordData):
    rec = recordData
    rec = rec.replace("\n\t", "")
    rec = rec.replace('\n\n    ', '\n\n')
    indexEndDecoration = rec.find("*/")
    self.addParamFromTypedef(rec[0:indexEndDecoration + 2])

  def declareFunctions(self):
    sDeclareFunstion = ''
    for returnValue in self.methodsRetuns:
      sDeclareFunstion += 'declare function ' + returnValue["sMethodName"] + '(): ' + returnValue["sRetunsType"] + '\n'
    return sDeclareFunstion

  def saveMethodReturn(self, alias, description):
    if '' == alias:
      return
    arrInfo = description.split('*')
    oReturn = {"sMethodName": alias, "sRetunsType": "undefined"}

    for info in arrInfo:
      if -1 != info.find('@returns'):
        oReturn["sRetunsType"] = self.getParamTypeFromLine(info)
    if "undefined" != oReturn["sRetunsType"] and True == self.is_typedef_param('{' + oReturn["sRetunsType"].replace('[', '').replace(']', '').replace('?', '') + '}'):
      oReturn["sRetunsType"] = oReturn["sRetunsType"].replace(oReturn["sRetunsType"].replace('[', '').replace(']', '').replace('?', ''), self.get_typedef_param(oReturn["sRetunsType"].replace('[', '').replace(']', '').replace('?', '')))

    self.methodsRetuns.append(oReturn)

  def check_record_for_plugin_api(self, recordData):
    rec = recordData
    rec = rec.replace('\n\n    ', '\n\n')
    indexEndDecoration = rec.find("*/")
    decoration = ""
    alias = self.getAlias(rec[0:indexEndDecoration + 2])
    paramsMap = self.getParams(rec[0:indexEndDecoration + 2].replace("\n\t", ""))
    self.saveMethodReturn(alias, rec[0:indexEndDecoration + 2].replace("\n\t", ""))
    returnValue = "undefined"

    codeInterface = self.createMethodInterface(alias, paramsMap, returnValue)
    if ('' != alias):
      decoration = "\t/**" + rec[0:indexEndDecoration] + '*/'
      decoration = decoration.replace("@return ", "@returns ")
      decoration = decoration.replace("@returns {?", "@returns {")
      decoration = self.deleteExcessDecor(decoration)

    if ('' != decoration):
      self.append_record(decoration, codeInterface)
    return
  def check_record_for_builder_api(self, recordData):
    rec = recordData
    rec = rec.replace("\t", "")
    rec = rec.replace('\n    ', '\n')
    indexEndDecoration = rec.find("*/")
    decoration = "/**" + rec[0:indexEndDecoration + 2]
    decoration = decoration.replace("Api\n", "ApiInterface\n")
    decoration = decoration.replace("Api ", "ApiInterface ")
    decoration = decoration.replace("{Api}", "{ApiInterface}")
    decoration = decoration.replace("@return ", "@returns ")
    decoration = decoration.replace("@returns {?", "@returns {")
    if -1 != decoration.find("@name ApiInterface"):
      self.append_record(decoration, "var ApiInterface = function() {};\nvar Api = new ApiInterface();\n", True)
      return
    code = rec[indexEndDecoration + 2:]
    code = code.strip("\t\n\r ")
    lines = code.split("\n")
    codeCorrect = ""
    sFuncName = ""
    is_found_function = False
    addon_for_func = "{}"
    if -1 != decoration.find("@return"):
      addon_for_func = "{ return null; }"
    for line in lines:
      line = line.strip("\t\n\r ")
      line = line.replace("{", "")
      line = line.replace("}", "")
      lineWithoutSpaces = line.replace(" ", "")
      if not is_found_function and 0 == line.find("function "):
        codeCorrect += (line + addon_for_func + "\n")
        is_found_function = True
      if not is_found_function and -1 != line.find(".prototype."):
        codeCorrect += (line + self.getReturnValue(decoration) + ";\n")
        is_found_function = True
      if -1 != lineWithoutSpaces.find(".prototype="):
        codeCorrect += (line + "\n")
      if -1 != line.find(".prototype.constructor"):
        codeCorrect += (line + "\n")
    codeCorrect = codeCorrect.replace("Api.prototype", "ApiInterface.prototype")
    self.append_record(decoration, codeCorrect)
    return
  # удаляем из описания все лишнее
  def deleteExcessDecor(self, decoration):
    allDecorLines = decoration.split('\n')
    arrLineForDelete = []
    resultDocoration = ''
    for nLine in range(len(allDecorLines)):
      if -1 != allDecorLines[nLine].find('@alias') or -1 != allDecorLines[nLine].find('@memberof') or -1 != allDecorLines[nLine].find('@typeofeditors') or -1 != allDecorLines[nLine].find('@returns') or -1 != allDecorLines[nLine].find('@this'):
        arrLineForDelete.append(allDecorLines[nLine])
    for line in arrLineForDelete:
      allDecorLines.remove(line)
    for line in allDecorLines:
      resultDocoration += line + '\n'
    return '\n' + resultDocoration.rstrip('\n')

  # перебиваем typedef объявления в удобную форму
  def addParamFromTypedef(self, decoration):
    arrInfo = []
    complexParams = []
    isObject = False
    isAlreadyAdded = False
    typedefParam = {"sName": "", "sType": "", "isFullFilled": False}
    if -1 != decoration.find('@typedef'):
      arrInfo = decoration.split('*')
    if -1 != decoration.find('@property'):
      isObject = True
      typedefParam["sType"] = {}

    for info in arrInfo:
      if -1 != info.find('@typedef'):
        typedefParam["sName"] = self.getParamNameFromLine(info)
        if False == isObject:
          typedefParam["sType"] = self.getParamTypeFromLine(info)
          break
      if -1 != info.find('@property'):
        sPropName = self.getParamNameFromLine(info)
        sPropType = self.getParamTypeFromLine(info)
        for nParam in range(len(complexParams)):
          complexParamName = complexParams[nParam]["sName"]
          if 0 == sPropName.find(complexParamName) and -1 == sPropName.lower().find('object'):
            trueParamName = sPropName.split(complexParamName + '.')[1]
            if (len(trueParamName.split('.')) == 1):
              complexParams[nParam]["sType"][trueParamName] = sPropType
              isAlreadyAdded = True
        if type(sPropType) is not dict and -1 != sPropType.lower().find('object'):
          complexParams.append({"sName": sPropName, "sType": {}})
        elif False == isAlreadyAdded:
          typedefParam['sType'][sPropName] = sPropType
    complexParams = self.compareComplexParams(complexParams)
    for param in complexParams:
      typedefParam['sType'][param['sName']] = param['sType'].replace('"','')

    if "" != typedefParam["sName"]:
      self.typedefParams.append(typedefParam)

  def fill_all_typedef_params(self):
    for nParam in range(len(self.typedefParams)):
      if type(self.typedefParams[nParam]['sType']) is dict:
        for key in self.typedefParams[nParam]['sType'].keys():
          if True == self.is_typedef_param('{' + self.typedefParams[nParam]['sType'][key].replace('[','').replace(']','').replace('?', '') + '}') and False == self.typedefParams[nParam]['isFullFilled']:
            self.typedefParams[nParam]['sType'][key] = self.fill_typedef_param(self.typedefParams[nParam]['sType'][key].replace('[','').replace(']','').replace('{','').replace('}','').replace('?', ''))
      self.typedefParams[nParam]['isFullFilled'] = True

  def fill_typedef_param(self, sTypedefParam):
    # находим параметр с заданным именем, заполняем внутренние поля-typedef'ы, если они есть
    for nParam in range(len(self.typedefParams)):
      if self.typedefParams[nParam]['sName'] == sTypedefParam:
        if type(self.typedefParams[nParam]['sType']) is dict:
          for key in self.typedefParams[nParam]['sType']:
            if True == self.is_typedef_param('{' + self.typedefParams[nParam]['sType'][key].replace('[','').replace(']','').replace('?', '') + '}'):
              self.typedefParams[nParam]['sType'][key] = self.fill_typedef_param(self.typedefParams[nParam]['sType'][key].replace('[','').replace(']','').replace('{','').replace('}','').replace('?', ''))
        self.typedefParams[nParam]["isFullFilled"] = True
        #return json.dumps(self.typedefParams[nParam]['sType']).replace('\\','').replace('"','') if type(self.typedefParams[nParam]['sType']) is dict else self.typedefParams[nParam]['sType']
        return self.getDictAsObject(self.typedefParams[nParam]['sType']) if type(self.typedefParams[nParam]['sType']) is dict else self.typedefParams[nParam]['sType']
    return ''
  def getDictAsObject(self, dictionary):
    result = ''
    for key in dictionary:
      if type(dictionary[key]) is dict:
        result += self.getDictAsObject(dictionary[key])
      else:
        result += key + ': ' + dictionary[key] + ', '
    return '{' + result.rstrip(', ') + '}'

  def is_typedef_param(self, paramType):
    if -1 != paramType.lower().find('{uint8array}'):
      return False
    if -1 != paramType.lower().find('{object}'):
      return False
    if -1 != paramType.lower().find('{number}'):
      return False
    if -1 != paramType.lower().find('{string}'):
      return False
    if -1 != paramType.lower().find('"'):
      return False
    if -1 != paramType.lower().find(':'):
      return False
    if -1 != paramType.lower().find('{bool}'):
      return False
    if -1 != paramType.lower().find('{boolean}'):
      return False
    if True == paramType.split('|')[0].replace('[','').replace('{','').replace(' ','').isdigit():
      return False
    return True

  def append_record(self, decoration, codeInterface, init=False):
    if init:
      if not self.init:
        self.init = True
        self.records.append(decoration + "\n" + codeInterface + "\n")
      return
    # check on private
    if -1 != codeInterface.find(".prototype.private_"):
      return
    # add records only for current editor
    index_type_editors = decoration.find("@typeofeditors")
    if -1 != index_type_editors:
      index_type_editors_end = decoration.find("]", index_type_editors)
      if -1 != index_type_editors_end:
        editors_support = decoration[index_type_editors:index_type_editors_end]
        if -1 == editors_support.find(self.type):
          return
    # optimizations for first file
    if 0 == self.numfile:
      self.records.append(decoration + "\n" + codeInterface + "\n")
      return
    # check override js classes
    if 0 == codeInterface.find("function "):
      index_end_name = codeInterface.find("(")
      function_name = codeInterface[9:index_end_name].strip(" ")
      for rec in range(len(self.records)):
        if -1 != self.records[rec].find("function " + function_name + "("):
          self.records[rec] = ""
        elif -1 != self.records[rec].find("function " + function_name + " ("):
          self.records[rec] = ""
        elif -1 != self.records[rec].find("\n\n" + function_name + ".prototype."):
          self.records[rec] = ""

    self.records.append(decoration + "\n\n" + codeInterface + "\n\n")
    return

  def generate_for_plugins_api(self):
    for file in self.files:
      file_content = readFile(file)
      arrRecords = file_content.split("/**")
      arrRecords = arrRecords[1:-1]
      for record in arrRecords:
        self.add_all_typedef_params(record)
      self.fill_all_typedef_params()
      for record in arrRecords:
        self.check_record_for_plugin_api(record)
      self.numfile += 1
    correctContent = self.declareFunctions()
    correctContent += 'interface IPlugin {\n'
    correctContent += ''.join(self.records) + '}\ninterface IAsc {\n\tPlugin: IPlugin;\n}\n\ndeclare var Asc: IAsc;\n\n'
    os.mkdir(old_cur + '//lib//api_plugins//' + self.folder)
    writeFile(old_cur + "//lib//api_plugins//" + self.folder + "//lib.onlyoffice.ts", correctContent)
    return

  def generate_for_builder_api(self):
    #global old_cur
    for file in self.files:
      file_content = readFile(file)
      arrRecords = file_content.split("/**")
      arrRecords = arrRecords[1:-1]
      for record in arrRecords:
        self.check_record_for_builder_api(record)
      self.numfile += 1
    correctContent = ''.join(self.records)
    correctContent += "\n"
    os.mkdir(old_cur + '//lib//api_builder//' + self.folder)
    writeFile(old_cur + "//lib//api_builder//" + self.folder + "/api.js", correctContent)
    return

def convert_to_interface(arrFiles, sEditorType, sInterfaceType):
  editor = EditorApi()
  editor.initFiles(sEditorType, arrFiles)
  if "builder" == sInterfaceType:
    editor.generate_for_builder_api()
  elif "plugins" == sInterfaceType:
    editor.generate_for_plugins_api()
  return

config = '{\n\
  "name": "hello world",\n\
  "guid": "asc.{' + str(uuid.uuid4()) + '}",\n\
  "baseUrl": "",\n\
  "variations": [\n\
    {\n\
      "description": "hello world",\n\
      "url": "index.html",\n\
      "icons": [ "resources/light/icon.png", "resources/light/icon@2x.png" ],\n\
      "icons2": [\n\
          {\n\
              "style" : "light",\n\
\n\
              "100%": {\n\
                  "normal": "resources/light/icon.png"\n\
              },\n\
              "150%": {\n\
                  "normal": "resources/light/icon@1.5x.png"\n\
              },\n\
              "200%": {\n\
                  "normal": "resources/light/icon@2x.png"\n\
              }\n\
          },\n\
          {\n\
              "style" : "dark",\n\
\n\
              "100%": {\n\
                  "normal": "resources/dark/icon.png"\n\
              },\n\
              "150%": {\n\
                  "normal": "resources/dark/icon@1.5x.png"\n\
              },\n\
              "200%": {\n\
                  "normal": "resources/dark/icon@2x.png"\n\
              }\n\
          }\n\
      ],\n\
      "isViewer": false,\n\
      "EditorsSupport": ["word"],\n\
      "isVisual": false,\n\
      "isModal": true,\n\
      "isInsideMode": false,\n\
      "initDataType": "none",\n\
      "initData": "",\n\
      "isUpdateOleOnResize": true,\n\
      "buttons": []\n\
    },\n\
    {\n\
      "description": "About",\n\
      "url": "index_about.html",\n\
      "icons": [ "resources/light/icon.png", "resources/light/icon@2x.png" ],\n\
      "icons2": [\n\
          {\n\
              "style" : "light",\n\
\n\
              "100%": {\n\
                  "normal": "resources/light/icon.png"\n\
              },\n\
              "150%": {\n\
                  "normal": "resources/light/icon@1.5x.png"\n\
              },\n\
              "200%": {\n\
                  "normal": "resources/light/icon@2x.png"\n\
              }\n\
          },\n\
          {\n\
              "style" : "dark",\n\
\n\
              "100%": {\n\
                  "normal": "resources/dark/icon.png"\n\
              },\n\
              "150%": {\n\
                  "normal": "resources/dark/icon@1.5x.png"\n\
              },\n\
              "200%": {\n\
                  "normal": "resources/dark/icon@2x.png"\n\
              }\n\
          }\n\
      ],\n\
      "isViewer": false,\n\
      "EditorsSupport": ["word"],\n\
      "isVisual": true,\n\
      "isModal": true,\n\
      "isInsideMode": false,\n\
      "initDataType": "none",\n\
      "initData": "",\n\
      "isUpdateOleOnResize": true,\n\
      "buttons": [\n\
        {\n\
          "text": "Ok",\n\
          "primary": true\n\
        }\n\
      ],\n\
\n\
      "size": [392, 147]\n\
    }\n\
  ]\n\
}'

index_html = '<!--\n\
 (c) Copyright Ascensio System SIA 2020\n\
\n\
 Licensed under the Apache License, Version 2.0 (the "License");\n\
 you may not use this file except in compliance with the License.\n\
 You may obtain a copy of the License at\n\
\n\
     http://www.apache.org/licenses/LICENSE-2.0\n\
\n\
 Unless required by applicable law or agreed to in writing, software\n\
 distributed under the License is distributed on an "AS IS" BASIS,\n\
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n\
 See the License for the specific language governing permissions and\n\
 limitations under the License.\n\
 -->\n\
<!DOCTYPE html>\n\
<html>\n\
<head>\n\
    <meta charset="UTF-8" />\n\
    <title>Hello world</title>\n\
    <script type="text/javascript" src="https://onlyoffice.github.io/sdkjs-plugins/v1/plugins.js"></script>\n\
    <script type="text/javascript" src="https://onlyoffice.github.io/sdkjs-plugins/v1/plugins-ui.js"></script>\n\
    <link rel="stylesheet" href="https://onlyoffice.github.io/sdkjs-plugins/v1/plugins.css">\n\
    <script type="text/javascript" src="scripts/code.js"></script>\n\
</head>\n\
<body>\n\
</body>\n\
</html>'

code = '/**\n\
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
\n\
// Example insert text into editors (different implementations)\n\
(function(window, undefined){\n\
\n\
    var sText = "Hello world!";\n\
\n\
    window.Asc.plugin.init = function()\n\
    {\n\
        var variant = 2;\n\
\n\
        switch (variant)\n\
        {\n\
            case 0:\n\
            {\n\
                // serialize command as text\n\
                var sScript = "var oDocument = Api.GetDocument();";\n\
                sScript += "oParagraph = Api.CreateParagraph();";\n\
                sScript += "oParagraph.AddText(" + sText + ");";\n\
                sScript += "oDocument.InsertContent([oParagraph]);";\n\
                this.info.recalculate = true;\n\
                this.executeCommand("close", sScript);\n\
                break;\n\
            }\n\
            case 1:\n\
            {\n\
                // call command without external variables\n\
                this.callCommand(function() {\n\
                    var oDocument = Api.GetDocument();\n\
                    var oParagraph = Api.CreateParagraph();\n\
                    oParagraph.AddText("Hello world!");\n\
                    oDocument.InsertContent([oParagraph]);\n\
                }, true);\n\
                break;\n\
            }\n\
            case 2:\n\
            {\n\
                // call command with external variables\n\
                Asc.scope.text = sText; // export variable to plugin scope\n\
                this.callCommand(function() {\n\
                    var oDocument = Api.GetDocument();\n\
                    var oParagraph = Api.CreateParagraph();\n\
                    oParagraph.AddText(Asc.scope.text); // or oParagraph.AddText(scope.text);\n\
                    oDocument.InsertContent([oParagraph]);\n\
                }, true);\n\
                break;\n\
            }\n\
            default:\n\
                break;\n\
        }\n\
    };\n\
\n\
    window.Asc.plugin.button = function(id)\n\
    {\n\
    };\n\
\n\
})(window, undefined);'

readme = '## Overview\n\
\n\
This simple plugin is designed to show the basic functionality of ONLYOFFICE Document Editor plugins. It inserts the "Hello World!" phrase when you press the button.\n\
\n\
It is without interface plugin and is not installed by default in cloud, [self-hosted](https://github.com/ONLYOFFICE/DocumentServer) and [desktop version](https://github.com/ONLYOFFICE/DesktopEditors) of ONLYOFFICE editors. \n\
\n\
## How to use\n\
\n\
1. Open the Plugins tab and press "hello world".\n\
\n\
If you need more information about how to use or write your own plugin, please see this https://api.onlyoffice.com/plugin/basic'


writeFile('./config.json', config)
writeFile('./index.html', index_html)
writeFile('./README.md', readme)

if True == os.path.isdir('./scripts'):
  shutil.rmtree('./scripts', ignore_errors=True)
os.mkdir('./scripts')
writeFile('./scripts/code.js', code)

# documentation
old_cur = os.getcwd()
os.chdir("../../../sdkjs")
if True == os.path.isdir(old_cur + '/lib'):
  shutil.rmtree(old_cur + '/lib', ignore_errors=True)
os.mkdir(old_cur + '/lib')
if True == os.path.isdir('lib/api_plugins'):
  shutil.rmtree('lib/api_plugins', ignore_errors=True)
os.mkdir(old_cur + '/lib/api_plugins')
if True == os.path.isdir('lib/api_builder'):
  shutil.rmtree('lib/api_builder', ignore_errors=True)
os.mkdir(old_cur + '/lib/api_builder')

convert_to_interface(["common/apiBase_plugins.js"], "common", "plugins")
convert_to_interface(["word/api_plugins.js"], "word", "plugins")
convert_to_interface(["cell/api_plugins.js"], "slide", "plugins")
convert_to_interface(["slide/api_plugins.js"], "cell", "plugins")

convert_to_interface(["word/apiBuilder.js"], "word", "builder")
convert_to_interface(["word/apiBuilder.js", "slide/apiBuilder.js"], "slide", "builder")
convert_to_interface(["word/apiBuilder.js", "slide/apiBuilder.js", "cell/apiBuilder.js"], "cell", "builder")
