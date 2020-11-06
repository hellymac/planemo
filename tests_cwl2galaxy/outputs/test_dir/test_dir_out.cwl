class: CommandLineTool
cwlVersion: v1.0
baseCommand: ls

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: test/example.txt
        entry: |-
          PREFIX='Message is:'
          MSG="\${PREFIX} $(inputs.message)"
          echo \${MSG}
      - entryname: test/example2.txt
        entry: "hello 2"
      - entryname: test/example3.txt
        entry: "hello 3"
      - entryname: test/example.sh
        entry: "shoud not be returned"


inputs:
  message: string
outputs:
  example_array_out:
    type: Directory
    outputBinding:
      glob: test
