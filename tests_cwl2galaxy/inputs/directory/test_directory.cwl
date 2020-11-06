#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
inputs:
  dir:
    type: Directory
    inputBinding:
      position: 1
outputs: []
baseCommand: ls
