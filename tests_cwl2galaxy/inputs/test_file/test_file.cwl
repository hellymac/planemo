#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
inputs:
  file:
    type: File
    inputBinding:
      position: 1
outputs: []
baseCommand: cat

