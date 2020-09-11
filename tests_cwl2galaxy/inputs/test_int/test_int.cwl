#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
baseCommand: echo
inputs:
  test_int:
    type: int
    inputBinding:
      position: 1
outputs: []
