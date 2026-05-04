# QueryFlow Installation Guide

QueryFlow is distributed as a Windows `.exe` in the project’s GitHub Releases page. You do not need Python installed to run the release build.

## Install

1. Open the QueryFlow repository on GitHub.
2. Go to **Releases**.
3. Download the latest release asset for Windows, usually a `.zip` file containing `QueryFlow.exe`.
4. Extract the archive to a folder on your computer.
5. Keep the `QueryFlow.exe` together with the `data/` and `examples/` folders if they are included in the release package.

## Run

Open a terminal in the folder that contains the executable and run one of these commands:

```powershell
QueryFlow.exe examples\example1_basic_fetch.qf -x
```

```powershell
QueryFlow.exe examples\example2_fetch_filter.qf -x
```

If you want to use your own QueryFlow file:

```powershell
QueryFlow.exe path\to\your_file.qf -x
```

## Notes

- Run the executable from the folder that contains the `examples/` and `data/` directories so relative paths resolve correctly.
- If Windows shows a security prompt, choose **More info** and then **Run anyway** if you trust the release.
- If the release is packaged as a single `.exe` only, place your `.qf` files and any data files in the same directory or use absolute paths.

## Common Commands

- `QueryFlow.exe <file.qf>`: Compile and display generated Python.
- `QueryFlow.exe <file.qf> -o output.py`: Compile and save the generated Python.
- `QueryFlow.exe <file.qf> -x`: Compile and execute the pipeline.
- Launch with no file to use the interactive shell.
