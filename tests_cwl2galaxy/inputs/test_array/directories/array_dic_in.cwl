#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool

inputs:
  - id: Dirs
    type:
      type: array
      items: Directory
    inputBinding:
      position: 1

outputs: []
baseCommand: echo
