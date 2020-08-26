#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
baseCommand: echo
inputs:
  - id: message
    type: string
    inputBinding:
      position: 1
  - id: test_int
    type: int
    default: 3
  - id: test_File
    type: File?
outputs:
  test_out:
    type: int?

