#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 19 09:49:25 2020

@author: cjuigne
"""
"""Module describing the planemo ``tool_cwl2galaxy`` command."""
import sys
import click
import yaml
from planemo import options
from planemo import tool_builder
from planemo.cli import command_function
from planemo import tool_cwltool

# add name option to name the output file
@click.command("cwl2galaxy")
@options.force_option(what="tool")
@options.cwl2galaxy_tool_option()
@click.option('filename', '--path',  type=click.Path(exists=True)) # TODO: options.cwl2galaxy_path_option
@command_function
def cli(ctx, filename, **kwds):
    """Generate tool outline from given CWL file."""
    tool = tool_cwltool.get_tool(ctx, filename)
    tool_description = tool_builder.build_cwl2galaxy(tool, filename, **kwds)
    tool_builder.write_tool(ctx, tool_description, **kwds)