#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool
baseCommand: echo
inputs:
  message:
    type: string
    inputBinding:
      position: 1
  test_int:
    type: int
    default: 3
  test_File:
    type: File?
outputs: []

