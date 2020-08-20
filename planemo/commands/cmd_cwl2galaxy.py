#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 19 09:49:25 2020

@author: cjuigne
"""
"""Module describing the planemo ``tool_cwl2galaxy`` command."""

import click
import yaml

from planemo import options
from planemo import tool_builder
from planemo.cli import command_function

# add name option to name the output file
@click.command("cwl2galaxy")
@options.force_option(what="tool")
@options.cwl2galaxy_tool_option()
@click.option('filename', '--path',  type=click.Path(exists=True)) # TODO: options.cwl2galaxy_path_option
@command_function
def cli(ctx, filename, **kwds):
    """Generate tool outline from given CWL file."""
    file = open(filename, "r")
    file_str = file.read()
    file_yml = yaml.load(file_str, Loader=yaml.CLoader)
    tool_description = tool_builder.build_cwl2galaxy(file_yml, **kwds)
    tool_builder.write_tool(ctx, tool_description, **kwds)
    file.close()