# geofileops API documentation

## Official sources

- API reference: https://geofileops.readthedocs.io/en/stable/reference.html
- User guide: https://geofileops.readthedocs.io/en/stable/user_guide.html
- Source code: https://github.com/geofileops/geofileops

## Instructions

When a Python task depends on geofileops behavior or APIs:

1. Check the geofileops version specified by the project's dependency files. When the active environment is available and the installed version matters, verify that version too.
2. Consult the official documentation for the relevant function. Check its dedicated API page for the exact signature, parameter names, defaults, types, return value, and version-specific behavior.
3. Prefer documentation matching the project's installed version. If the documentation and installed API differ, prioritize compatibility with the installed version and explain the discrepancy.
4. Do not invent or assume functions, parameters, defaults, return values, or behavior. If a detail cannot be verified, say so and label any assumption explicitly.
5. If the documentation is unavailable or incomplete, state that. Consult the official source for the relevant release when needed, and distinguish source-verified details from documentation-verified details.
6. In your response, link to the specific documentation page consulted whenever possible.

## Implementation guidance

- Follow the verified API and the project's existing coding patterns.
- Keep changes focused. Add error handling only where it is useful and consistent with the project; do not silently swallow errors.
- Consider performance and memory use when processing large datasets.
- Preserve the requested and existing input/output formats. Use GeoPackage when appropriate, not as an assumed requirement.
- Add an `if __name__ == "__main__":` guard when a standalone script uses multiprocessing and its execution environment requires one.
- Do not add dependencies unless the task requires them.