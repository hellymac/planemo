#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
baseCommand: echo
inputs:
  test_string:
    type: string
    inputBinding:
      position: 1
outputs: []
