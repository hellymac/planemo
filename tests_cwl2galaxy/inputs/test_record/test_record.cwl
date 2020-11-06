#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
inputs:
  dependent_parameters:
    type:
      type: record
      name: dependent_parameters
      fields:
        itemA:
          type: string
          inputBinding:
            prefix: -A
        itemB:
          type: string
          inputBinding:
            prefix: -B
        itemC:
          type: File
          inputBinding:
            position: 1
  # exclusive_parameters:
  #   type:
  #     - type: record
  #       name: itemC
  #       fields:
  #         itemC:
  #           type: string
outputs: []
baseCommand: echo
