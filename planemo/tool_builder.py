"""This module contains :func:`build` to build tool descriptions.

This class is used by the `tool_init` command and can be used to build
Galaxy and CWL tool descriptions.
"""

import os
import re
import shlex
import shutil
import subprocess
from collections import namedtuple

from planemo import io
from planemo import templates
#from galaxy.lib.galaxy.tool_util.cwl import representation

REUSING_MACROS_MESSAGE = ("Macros file macros.xml already exists, assuming "
                          " it has relevant planemo-generated definitions.")
DEFAULT_CWL_VERSION = "v1.0"


TOOL_TEMPLATE = """<tool id="{{id}}" name="{{name}}" version="{{version}}" python_template_version="3.5">
{%- if description %}
    <description>{{ description }}</description>
{%- endif %}
{%- if macros %}
    <macros>
        <import>macros.xml</import>
    </macros>
    <expand macro="requirements" />
{%- if version_command %}
    <expand macro="version_command" />
{%- endif %}
{%- else %}
    <requirements>
{%- for requirement in requirements %}
        {{ requirement }}
{%- endfor %}
{%- for container in containers %}
        {{ container }}
{%- endfor %}
    </requirements>
{%- if version_command %}
    <version_command>{{ version_command }}</version_command>
{%- endif %}
{%- endif %}
    <command detect_errors="exit_code"><![CDATA[
{%- if command %}
        {{ command }}
{%- else %}
        TODO: Fill in command template.
{%- endif %}
    ]]></command>
    <inputs>
{%- for input in inputs %}
        {{ input }}
{%- endfor %}
    </inputs>
    <outputs>
{%- for output in outputs %}
        {{ output }}
{%- endfor %}
    </outputs>
{%- if tests %}
    <tests>
{%- for test in tests %}
        <test>
{%- for param in test.params %}
            <param name="{{ param[0]}}" value="{{ param[1] }}"/>
{%- endfor %}
{%- for output in test.outputs %}
            <output name="{{ output[0] }}" file="{{ output[1] }}"/>
{%- endfor %}
        </test>
{%- endfor %}
    </tests>
{%- endif %}
    <help><![CDATA[
{%- if help %}
        {{ help }}
{%- else %}
        TODO: Fill in help.
{%- endif %}
    ]]></help>
{%- if macros %}
    <expand macro="citations" />
{%- else %}
{%- if doi or bibtex_citations %}
    <citations>
{%- for single_doi in doi %}
        <citation type="doi">{{ single_doi }}</citation>
{%- endfor %}
{%- for bibtex_citation in bibtex_citations %}
        <citation type="bibtex">{{ bibtex_citation }}</citation>
{%- endfor %}
    </citations>
{%- endif %}
{%- endif %}
</tool>
"""

MACROS_TEMPLATE = """<macros>
    <xml name="requirements">
        <requirements>
{%- for requirement in requirements %}
        {{ requirement }}
{%- endfor %}
            <yield/>
{%- for container in containers %}
        {{ container }}
{%- endfor %}
        </requirements>
    </xml>
    <xml name="citations">
        <citations>
{%- for single_doi in doi %}
            <citation type="doi">{{ single_doi }}</citation>
{%- endfor %}
{%- for bibtex_citation in bibtex_citations %}
            <citation type="bibtex">{{ bibtex_citation }}</citation>
{%- endfor %}
            <yield />
        </citations>
    </xml>
{%- if version_command %}
    <xml name="version_command">
        <version_command>{{ version_command }}</version_command>
    </xml>
{%- endif %}
</macros>
"""

CWL_TEMPLATE = """#!/usr/bin/env cwl-runner
cwlVersion: '{{cwl_version}}'
class: CommandLineTool
id: "{{id}}"
label: "{{label}}"
{%- if containers or requirements %}
hints:
{%- for container in containers %}
  DockerRequirement:
    dockerPull: {{ container.image_id }}
{%- endfor %}
{%- if requirements %}
  SoftwareRequirement:
    packages:
{%- for requirement in requirements %}
    - package: {{ requirement.name }}
{%- if requirement.version %}
      version:
      - "{{ requirement.version }}"
{%- else %}
      version: []
{%- endif %}
{%- endfor %}
{%- endif %}
{%- endif %}
{%- if inputs or outputs %}
inputs:
{%- for input in inputs %}
  {{ input.id }}:
    type: {{ input.type }}
    doc: |
      TODO
    inputBinding:
      position: {{ input.position }}
{%- if input.prefix %}
      prefix: "{{input.prefix.prefix}}"
{%- if not input.prefix.separated %}
      separate: false
{%- endif %}
{%- endif %}
{%- endfor %}
{%- for output in outputs %}
{%- if output.require_filename %}
  {{ output.id }}:
    type: string
    doc: |
      Filename for output {{ output.id }}
    inputBinding:
      position: {{ output.position }}
{%- if output.prefix %}
      prefix: "{{output.prefix.prefix}}"
{%- if not output.prefix.separated %}
      separate: false
{%- endif %}
{%- endif %}
{%- endif %}
{%- endfor %}
{%- else %}
inputs: [] # TODO
{%- endif %}
{%- if outputs %}
outputs:
{%- for output in outputs %}
  {{ output.id }}:
    type: File
    outputBinding:
      glob: {{ output.glob }}
{%- endfor %}
{%- else %}
outputs: [] # TODO
{%- endif %}
{%- if base_command %}
baseCommand:
{%- for base_command_part in base_command %}
  - "{{ base_command_part}}"
{%- endfor %}
{%- else %}
baseCommand: []
{%- endif %}
{%- if arguments %}
arguments:
{%- for argument in arguments %}
  - valueFrom: "{{ argument.value }}"
    position: {{ argument.position }}
{%- if argument.prefix %}
      prefix: "{{argument.prefix.prefix}}"
{%- if not argument.prefix.separated %}
      separate: false
{%- endif %}
{%- endif %}
{%- endfor %}
{%- else %}
arguments: []
{%- endif %}
{%- if stdout %}
stdout: {{ stdout }}
{%- endif %}
doc: |
{%- if help %}
  {{ help|indent(2) }}
{%- else %}
   TODO: Fill in description.
{%- endif %}
"""

CWL_TEST_TEMPLATE = """
- doc: test generated from example command
  job: {{ job_filename }}
{%- if outputs %}
  outputs:
{%- for output in outputs %}
    {{ output.id }}:
      path: test-data/{{ output.example_value }}
{%- endfor %}
{%- else %}
  outputs: TODO
{%- endif %}
"""

CWL_JOB_TEMPLATE = """
{%- if inputs %}
{%- for input in inputs %}
{%- if input.type == "File" %}
{{ input.id }}:
  class: File
  path: test-data/{{ input.example_value }}
{%- else %}
  {{ input.id }}: {{ input.example_value }}
{%- endif %}
{%- endfor %}
{%- else %}
# TODO: Specify job input.
{}
{%- endif %}
"""


def build(**kwds):
    """Build up a :func:`ToolDescription` from supplid arguments."""
    if kwds.get("cwl"):
        builder = _build_cwl
    else:
        builder = _build_galaxy
    return builder(**kwds)


def _build_cwl(**kwds):
    _handle_help(kwds)
    _handle_requirements(kwds)
    assert len(kwds["containers"]) <= 1, kwds
    command_io = CommandIO(**kwds)
    render_kwds = {
        "cwl_version": DEFAULT_CWL_VERSION,
        "help": kwds.get("help", ""),
        "containers": kwds.get("containers", []),
        "requirements": kwds.get("requirements", []),
        "id": kwds.get("id"),
        "label": kwds.get("name"),
    }
    render_kwds.update(command_io.cwl_properties())

    contents = _render(render_kwds, template_str=CWL_TEMPLATE)
    tool_files = []
    test_files = []
    if kwds["test_case"]:
        sep = "-" if "-" in kwds.get("id") else "_"
        tests_path = "%s%stests.yml" % (kwds.get("id"), sep)
        job_path = "%s%sjob.yml" % (kwds.get("id"), sep)
        render_kwds["job_filename"] = job_path
        test_contents = _render(render_kwds, template_str=CWL_TEST_TEMPLATE)
        job_contents = _render(render_kwds, template_str=CWL_JOB_TEMPLATE)
        tool_files.append(ToolFile(tests_path, test_contents, "test"))
        tool_files.append(ToolFile(job_path, job_contents, "job"))
        for cwl_input in render_kwds["inputs"] or []:
            if cwl_input.type == "File" and cwl_input.example_value:
                test_files.append(cwl_input.example_value)

        for cwl_output in render_kwds["outputs"] or []:
            if cwl_output.example_value:
                test_files.append(cwl_output.example_value)

    return ToolDescription(
        contents,
        tool_files=tool_files,
        test_files=test_files
    )


def _build_galaxy(**kwds):
    # Test case to build up from supplied inputs and outputs, ultimately
    # ignored unless kwds["test_case"] is truthy.

    _handle_help(kwds)

    # process raw cite urls
    cite_urls = kwds.get("cite_url", [])
    del kwds["cite_url"]
    citations = list(map(UrlCitation, cite_urls))
    kwds["bibtex_citations"] = citations

    # handle requirements and containers
    _handle_requirements(kwds)

    command_io = CommandIO(**kwds)
    kwds["inputs"] = command_io.inputs
    kwds["outputs"] = command_io.outputs
    kwds["command"] = command_io.cheetah_template

    test_case = command_io.test_case()

    # finally wrap up tests
    tests, test_files = _handle_tests(kwds, test_case)
    kwds["tests"] = tests

    # Render tool content from template.
    contents = _render(kwds)

    tool_files = []
    append_macro_file(tool_files, kwds)

    return ToolDescription(
        contents,
        tool_files=tool_files,
        test_files=test_files
    )

###############  CWL 2 GALAXY  ####################
def write_command(inputs):
    """ write the tool XML command : create cwl job file """
    command = "touch job.yml \n"
    for i in inputs:
        if i.type == "string" or "int" or "float" or "boolean" or "long" or "double" or "enum":     
            command += "\'" +str(i.name)+": $"+(str(i.name))+ "\' >> job.yml \n" 
          # TODO : Format file
          # TODO : conditionnal
        if i.type == "File":
            command += "\'" + str(i.name) + ": \' >> job.yml \n"
            command += "\'  class: File \' >> job.yml \n"
            command += "\'  path: $" + str(i.name) +"\' >> job.yml \n" 
            if i.format: # TO DO : URI
                command += "\'  format: $" + str(i.format) + "\' >> job.yml \n"
        if i.type == "Directory":
            command += "\'" + str(i.name) + ": \' >> job.yml \n"
            command += "\'  class: Directory \' >> job.yml \n"
            command += "\'  path: $" + str(i.name) +"\' >> job.yml \n" 
    # TO DO : record /array
    command +="\n cwltool '$__tool_directory__/tool.cwl' '$__tool_directory__/job.yml "
    return command

def build_cwl2galaxy(file, **kwds):
    # process raw cite urls
    # cite_urls = kwds.get("cite_url", [])
    # del kwds["cite_url"]
    # citations = list(map(UrlCitation, cite_urls))
    # kwds["bibtex_citations"] = citations
    
    ### multiple="true" optional="true"
    tool = Cwl(file)
    kwds["tool"] = kwds.get("tool")
    kwds["id"] = tool.name
    kwds["name"] = tool.label
    kwds["command"] = write_command(tool.inputs) 
    kwds["requirements"] = [] # objet requirement
    kwds["help"] = tool.help
    kwds["inputs"] = tool.inputs
    kwds["outputs"] = tool.outputs
    kwds["macros"] = None 
    kwds["tests"] = []
    kwds["test_case"] = None
    kwds["version"] = "test version"
    
    # for input in tool.inputs:
    #     print(input.type)
    # command_io = CommandIO(**kwds)
    # test_case = command_io.test_case()
    # tests, test_files = _handle_tests(kwds, test_case)
    # kwds["tests"] = tests

 
    # Render tool content from template.
    contents = _render(kwds)
    # print("render")
    # print(contents)
    tool_files = []
    test_files = None
    
    return ToolDescription(
        contents,
        tool_files=tool_files,
        test_files=test_files
    )

def write_tool(ctx, tool_description, **kwds):
    """Write a tool description to the file system guided by supplied CLI kwds."""
    output = kwds.get("tool")
    if not io.can_write_to_path(output, **kwds):
        ctx.exit(1)

    io.write_file(output, tool_description.contents)
    io.info("Tool written to %s" % output)

# not used ?
    # for tool_file in tool_description.tool_files:
    #     if tool_file.contents is None:
    #         continue

    #     path = tool_file.filename
    #     if not io.can_write_to_path(path, **kwds):
    #         ctx.exit(1)
    #     io.write_file(path, tool_file.contents)
    #     io.info("Tool %s written to %s" % (tool_file.description, path))

# TODO add test_file option :
    # if tool_description.test_files:
    #     if not os.path.exists("test-data"):
    #         io.info("No test-data directory, creating one.")
    #         os.makedirs('test-data')
    #     for test_file in tool_description.test_files:
    #         io.info("Copying test-file %s" % test_file)
    #         try:
    #             shutil.copy(test_file, 'test-data')
    #         except Exception as e:
    #             io.info("Copy of %s failed: %s" % (test_file, e))
    
class Cwl:
    def __init__(self, dict):
        self.dict = dict
        if "id" in dict:
            self.name = dict["id"]
        else:
            self.name = "tool"
        if "label" in dict:
            self.label = dict["label"]
        else :
            self.label = self.name
        if "doc" in dict:
            self.help = dict["doc"]
        else:
            self.help = None
        
        self.nbinputs = len(dict["inputs"])
        self.inputs_names = list(self.dict["inputs"].keys())
        self.inputs = []
        for input in self.dict['inputs']:
            self.inputs.append(Input_cwl(self.dict['inputs'][input], input))

        self.nboutputs = len(dict["outputs"])
        self.outputs = []
        for output in self.dict['outputs']:
            self.outputs.append(Output_cwl(self.dict['outputs'][output], output))

class Input_cwl(object):

    def __init__(self, dict, name):
        # Changer type : corespondance avec Galaxy types
        self.name = name
        self.optional = False
        self.type = dict["type"]
        if self.type[-1]=='?' :
            self.optional = True
            self.type = self.type[:-1]
        self.type = CWL_TO_GALAXY_TYPES[self.type]
        if "label" in dict:
            self.label = dict["label"]
        else :
            self.label = name
        if "default" in dict:
            self.value = dict["default"]
        else :
            self.value = None
        if "doc" in dict:
            self.doc = dict["doc"]  
        else :
            self.doc = None
        if "format" in dict:
            self.format = dict["format"]    #trouver comment récup le format (RDF)
        else :
            self.format = None
    def __str__(self):
        template = '<param type="{0}" name="{1}" label="{2}" optional="{3}"'
        if self.value != None :
            template+=' value="{4}"'
        if self.doc != None :
            template+= ' help="{5}"'
        if self.format != None :
            template+=' format="{6}"/>' #format only if type is data
        template+='/>'
        return template.format(self.type, self.name, self.label, self.optional, self.value, self.doc, self.format)

class Output_cwl(object):
    def __init__(self, dict, name):
        self.name = name
        self.optional = False
        self.type = dict["type"]
        if self.type[-1]=='?' :
            self.optional = True
            self.type = self.type[:-1]
        self.type = CWL_TO_GALAXY_TYPES[self.type]
        if "label" in dict:
            self.label = dict["label"]
        else :
            self.label = name
        if "doc" in dict:
            self.doc = dict["doc"]  
        else :
            self.doc = None
        if "format" in dict:
            self.format = dict["format"]    # TODO : get format from URI ; get format from glob field 
        else :
            self.format = None
        if "outputBinding" in dict and "glob" in dict["outputBinding"]:
            self.from_path = dict["outputBinding"]["glob"]
        else:
            self.from_path = None
    def __str__(self):
        template = '<data name="{0}" format="{1}" ' # 'optional="{2}"'
        if self.doc != None :
            template+= ' help="{2}"'
        if self.from_path != None :
            template+= ' from_work_dir="{3}"'
        template+='/>'
        return template.format(self.name, self.format, self.doc, self.from_path)

CWL_TO_GALAXY_TYPES = {
    "string": "text",
    "int": "integer",
    "File": "data",
    "boolean": "boolean",
    "enum": "select",
    "double": "float",
    "long": "integer",
    "float": "float",
    "Directory": "data_collection",
    "Any": "field",
    "array": "data_collection",
    "null": "null",
    "record": "data_collection",
    }

# Galaxy types :  	Describes the parameter type - each different type as different semantics and the tool form widget is different. Currently valid parameter types are: text, integer, float, boolean, genomebuild, select, color, data_column, hidden, hidden_data, baseurl, file, ftpfile, data, data_collection, library_data, drill_down
# multiple :	Allow multiple valus to be selected. Valid with data and select parameters.
# {'text', 'integer', 'float', 'color', 'boolean', 'genomebuild', 'library_data', 
# 'select', 'data_column', 'hidden', 'hidden_data', 'baseurl', 'file', 'data', 
# 'drill_down', 'group_tag', 'data_collection'}

# Any
# null	no value
# boolean	a binary value
# int	32-bit signed integer
# long	64-bit signed integer
# float	single precision (32-bit) IEEE 754 floating-point number
# double	double precision (64-bit) IEEE 754 floating-point number
# string	Unicode character sequence
# File	A File object
# Directory	A Directory object
###############  CWL 2 GALAXY  #################### 
def append_macro_file(tool_files, kwds):
    macro_contents = None
    if kwds["macros"]:
        macro_contents = _render(kwds, MACROS_TEMPLATE)

        macros_file = "macros.xml"
        if not os.path.exists(macros_file):
            tool_files.append(ToolFile(macros_file, macro_contents, "macros"))

        io.info(REUSING_MACROS_MESSAGE)


class CommandIO(object):

    def __init__(self, **kwds):
        command = _find_command(kwds)
        cheetah_template = command

        # process raw inputs
        inputs = kwds.pop("input", [])
        inputs = list(map(Input, inputs or []))

        # alternatively process example inputs
        example_inputs = kwds.pop("example_input", [])
        for i, input_file in enumerate(example_inputs or []):
            name = "input%d" % (i + 1)
            inputs.append(Input(input_file, name=name, example=True))
            cheetah_template = _replace_file_in_command(cheetah_template, input_file, name)

        # handle raw outputs (from_work_dir ones) as well as named_outputs
        outputs = kwds.pop("output", [])
        outputs = list(map(Output, outputs or []))

        named_outputs = kwds.pop("named_output", [])
        for named_output in (named_outputs or []):
            outputs.append(Output(name=named_output, example=False))

        # handle example outputs
        example_outputs = kwds.pop("example_output", [])
        for i, output_file in enumerate(example_outputs or []):
            name = "output%d" % (i + 1)
            from_path = output_file
            use_from_path = True
            if output_file in cheetah_template:
                # Actually found the file in the command, assume it can
                # be specified directly and skip from_work_dir.
                use_from_path = False
            output = Output(name=name, from_path=from_path,
                            use_from_path=use_from_path, example=True)
            outputs.append(output)
            cheetah_template = _replace_file_in_command(cheetah_template, output_file, output.name)

        self.inputs = inputs
        self.outputs = outputs
        self.command = command
        self.cheetah_template = cheetah_template

    def example_input_names(self):
        for input in self.inputs:
            if input.example:
                yield input.input_description

    def example_output_names(self):
        for output in self.outputs:
            if output.example:
                yield output.example_path

    def cwl_lex_list(self):
        if not self.command:
            return []

        command_parts = shlex.split(self.command)
        parse_list = []

        input_count = 0
        output_count = 0

        index = 0

        prefixed_parts = []
        while index < len(command_parts):
            value = command_parts[index]
            eq_split = value.split("=")

            prefix = None
            if not _looks_like_start_of_prefix(index, command_parts):
                index += 1
            elif len(eq_split) == 2:
                prefix = Prefix(eq_split[0] + "=", False)
                value = eq_split[1]
                index += 1
            else:
                prefix = Prefix(value, True)
                value = command_parts[index + 1]
                index += 2
            prefixed_parts.append((prefix, value))

        for position, (prefix, value) in enumerate(prefixed_parts):
            if value in self.example_input_names():
                input_count += 1
                input = _CwlInput(
                    "input%d" % input_count,
                    position,
                    prefix,
                    value,
                )
                parse_list.append(input)
            elif value in self.example_output_names():
                output_count += 1
                output = _CwlOutput(
                    "output%d" % output_count,
                    position,
                    prefix,
                    value,
                )
                parse_list.append(output)
            elif prefix:
                param_id = prefix.prefix.lower().rstrip("=")
                type_ = param_type(value)
                input = _CwlInput(
                    param_id,
                    position,
                    prefix,
                    value,
                    type_=type_,
                )
                parse_list.append(input)
            else:
                part = _CwlCommandPart(value, position, prefix)
                parse_list.append(part)
        return parse_list

    def cwl_properties(self):
        base_command = []
        arguments = []
        inputs = []
        outputs = []

        lex_list = self.cwl_lex_list()

        index = 0
        while index < len(lex_list):
            token = lex_list[index]
            if isinstance(token, _CwlCommandPart):
                base_command.append(token.value)
            else:
                break
            index += 1

        while index < len(lex_list):
            token = lex_list[index]
            if token.is_token(">"):
                break
            token.position = index - len(base_command) + 1
            if isinstance(token, _CwlCommandPart):
                arguments.append(token)
            elif isinstance(token, _CwlInput):
                inputs.append(token)
            elif isinstance(token, _CwlOutput):
                token.glob = "$(inputs.%s)" % token.id
                outputs.append(token)

            index += 1

        stdout = None
        if index < len(lex_list):
            token = lex_list[index]
            if token.is_token(">") and (index + 1) < len(lex_list):
                output_token = lex_list[index + 1]
                if not isinstance(output_token, _CwlOutput):
                    output_token = _CwlOutput("std_out", None)

                output_token.glob = "out"
                output_token.require_filename = False
                outputs.append(output_token)
                stdout = "out"
                index += 2
            else:
                io.warn("Example command too complex, you will need to build it up manually.")

        return {
            "inputs": inputs,
            "outputs": outputs,
            "arguments": arguments,
            "base_command": base_command,
            "stdout": stdout,
        }

    def test_case(self):
        test_case = TestCase()
        for input in self.inputs:
            if input.example:
                test_case.params.append((input.name, input.input_description))

        for output in self.outputs:
            if output.example:
                test_case.outputs.append((output.name, output.example_path))

        return test_case


def _looks_like_start_of_prefix(index, parts):
    value = parts[index]
    if len(value.split("=")) == 2:
        return True
    if index + 1 == len(parts):
        return False
    next_value = parts[index + 1]
    next_value_is_not_start = (len(value.split("=")) != 2) and next_value[0] not in ["-", ">", "<", "|"]
    return value.startswith("-") and next_value_is_not_start


Prefix = namedtuple("Prefix", ["prefix", "separated"])


class _CwlCommandPart(object):

    def __init__(self, value, position, prefix):
        self.value = value
        self.position = position
        self.prefix = prefix

    def is_token(self, value):
        return self.value == value


class _CwlInput(object):

    def __init__(self, id, position, prefix, example_value, type_="File"):
        self.id = id
        self.position = position
        self.prefix = prefix
        self.example_value = example_value
        self.type = type_

    def is_token(self, value):
        return False


class _CwlOutput(object):

    def __init__(self, id, position, prefix, example_value):
        self.id = id
        self.position = position
        self.prefix = prefix
        self.glob = None
        self.example_value = example_value
        self.require_filename = True

    def is_token(self, value):
        return False


def _render(kwds, template_str=TOOL_TEMPLATE):
    """Render template variables to generate the final tool."""
    return templates.render(template_str, **kwds)


def _replace_file_in_command(command, specified_file, name):
    """Replace example file with cheetah variable name.

    Be sure to single quote the name.
    """
    # TODO: check if the supplied variant was single quoted already.
    if '"%s"' % specified_file in command:
        # Sample command already wrapped filename in double quotes
        command = command.replace('"%s"' % specified_file, "'$%s'" % name)
    elif (" %s " % specified_file) in (" " + command + " "):
        # In case of spaces, best to wrap filename in double quotes
        command = command.replace(specified_file, "'$%s'" % name)
    else:
        command = command.replace(specified_file, '$%s' % name)
    return command


def _handle_help(kwds):
    """Convert supplied help parameters into a help variable for template.

    If help_text is supplied, use as is. If help is specified from a command,
    run the command and use that help text.
    """
    help_text = kwds.get("help_text")
    if not help_text:
        help_from_command = kwds.get("help_from_command")
        if help_from_command:
            p = subprocess.Popen(
                help_from_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            help_text = p.communicate()[0]

    del kwds["help_text"]
    del kwds["help_from_command"]

    kwds["help"] = help_text


def _handle_tests(kwds, test_case):
    """Build tool test abstractions.

    Given state built up from handling rest of arguments (test_case) and
    supplied kwds - build tests for template and corresponding test files.
    """
    test_files = []
    if kwds["test_case"]:
        tests = [test_case]
        test_files.extend(map(lambda x: x[1], test_case.params))
        test_files.extend(map(lambda x: x[1], test_case.outputs))
    else:
        tests = []
    return tests, test_files


def _handle_requirements(kwds):
    """Build tool requirement abstractions.

    Convert requirements and containers specified from the command-line
    into abstract format for consumption by the template.
    """
    requirements = kwds["requirement"]
    del kwds["requirement"]
    requirements = list(map(Requirement, requirements or []))

    container = kwds["container"]
    del kwds["container"]
    containers = list(map(Container, container or []))

    kwds["requirements"] = requirements
    kwds["containers"] = containers


def _find_command(kwds):
    """Find base command from supplied arguments or just return `None`.

    If no such command was supplied (template will just replace this
    with a TODO item).
    """
    command = kwds.get("command")
    if not command:
        command = kwds.get("example_command", None)
        if command:
            del kwds["example_command"]
    return command


class UrlCitation(object):
    """Describe citation for tool."""

    def __init__(self, url):
        self.url = url

    def __str__(self):
        if "github.com" in self.url:
            return self._github_str()
        else:
            return self._url_str()

    def _github_str(self):
        url = self.url
        title = url.split("/")[-1]
        return '''
@misc{github%s,
  author = {LastTODO, FirstTODO},
  year = {TODO},
  title = {%s},
  publisher = {GitHub},
  journal = {GitHub repository},
  url = {%s},
}''' % (title, title, url)

    def _url_str(self):
        url = self.url
        return '''
@misc{renameTODO,
  author = {LastTODO, FirstTODO},
  year = {TODO},
  title = {TODO},
  url = {%s},
}''' % (url)


class ToolDescription(object):
    """An description of the tool and related files to create."""

    def __init__(self, contents, tool_files=None, test_files=[]):
        self.contents = contents
        self.tool_files = tool_files or []
        self.test_files = test_files


class ToolFile(object):

    def __init__(self, filename, contents, description):
        self.filename = filename
        self.contents = contents
        self.description = description


class Input(object):

    def __init__(self, input_description, name=None, example=False):
        parts = input_description.split(".")
        name = name or parts[0]
        if len(parts) > 0:
            datatype = ".".join(parts[1:])
        else:
            datatype = "data"

        self.input_description = input_description
        self.example = example
        self.name = name
        self.datatype = datatype

    def __str__(self):
        template = '<param type="data" name="{0}" format="{1}" />'
        self.datatype = self.datatype.split(".")[-1]
        return template.format(self.name, self.datatype)


class Output(object):

    def __init__(self, from_path=None, name=None, use_from_path=False, example=False):
        if from_path:
            parts = from_path.split(".")
            name = name or parts[0]
            if len(parts) > 1:
                datatype = ".".join(parts[1:])
            else:
                datatype = "data"
        else:
            name = name
            datatype = "data"

        self.name = name
        self.datatype = datatype
        if use_from_path:
            self.from_path = from_path
        else:
            self.from_path = None
        self.example = example
        if example:
            self.example_path = from_path

    def __str__(self):
        if self.from_path:
            return self._from_path_str()
        else:
            return self._named_str()

    def _from_path_str(self):
        template = '<data name="{0}" format="{1}" from_work_dir="{2}" />'
        return template.format(self.name, self.datatype, self.from_path)

    def _named_str(self):
        template = '<data name="{0}" format="{1}" />'
        return template.format(self.name, self.datatype)


class Requirement(object):

    def __init__(self, requirement):
        parts = requirement.split("@", 1)
        if len(parts) > 1:
            name = parts[0]
            version = "@".join(parts[1:])
        else:
            name = parts[0]
            version = None
        self.name = name
        self.version = version

    def __str__(self):
        base = '<requirement type="package"{0}>{1}</requirement>'
        if self.version is not None:
            attrs = ' version="{0}"'.format(self.version)
        else:
            attrs = ''
        return base.format(attrs, self.name)


def param_type(value):
    if re.match(r"^\d+$", value):
        return "int"
    elif re.match(r"^\d+?\.\d+?$", value):
        return "float"
    else:
        return "string"


class Container(object):

    def __init__(self, image_id):
        self.type = "docker"
        self.image_id = image_id

    def __str__(self):
        template = '<container type="{0}">{1}</container>'
        return template.format(self.type, self.image_id)


class TestCase(object):

    def __init__(self):
        self.params = []
        self.outputs = []


def write_tool_description(ctx, tool_description, **kwds):
    """Write a tool description to the file system guided by supplied CLI kwds."""
    tool_id = kwds.get("id")
    output = kwds.get("tool")
    if not output:
        extension = "cwl" if kwds.get("cwl") else "xml"
        output = "%s.%s" % (tool_id, extension)
    if not io.can_write_to_path(output, **kwds):
        ctx.exit(1)

    io.write_file(output, tool_description.contents)
    io.info("Tool written to %s" % output)
    for tool_file in tool_description.tool_files:
        if tool_file.contents is None:
            continue

        path = tool_file.filename
        if not io.can_write_to_path(path, **kwds):
            ctx.exit(1)
        io.write_file(path, tool_file.contents)
        io.info("Tool %s written to %s" % (tool_file.description, path))

    macros = kwds["macros"]
    macros_file = "macros.xml"
    if macros and not os.path.exists(macros_file):
        io.write_file(macros_file, tool_description.macro_contents)
    elif macros:
        io.info(REUSING_MACROS_MESSAGE)
    if tool_description.test_files:
        if not os.path.exists("test-data"):
            io.info("No test-data directory, creating one.")
            os.makedirs('test-data')
        for test_file in tool_description.test_files:
            io.info("Copying test-file %s" % test_file)
            try:
                shutil.copy(test_file, 'test-data')
            except Exception as e:
                io.info("Copy of %s failed: %s" % (test_file, e))


__all__ = (
    "build",
    "ToolDescription",
    "write_tool_description",
)
