# Python Script Data Flow Explanation

## 1. User Interaction
- The script begins with a call to `main()`.
- The `usage()` function is called to display information about script usage.
- The user is prompted to input a SQUAD Testrun URL or SQUAD Test URL.
- The entered URL is stored in the variable `URL`.

## 2. URL Validation and Selection
- The script checks if the provided URL is a Tuxtest URL using the `is_tuxtest_url()` function.
- If it is a Tuxtest URL, the script sets `job_url` to the provided URL.
- If not, the script tries to parse the URL to determine if it's a SQUAD Test ID or SQUAD Testrun ID.
- Based on the parsing results, the script retrieves the job URL (`job_url`) from the SQUAD API.

## 3. Fetching Tuxtest Reproducer
- The script constructs the Tuxtest reproducer URL (`tuxtest_reproducer_url`) based on the `job_url`.
- The content of the Tuxtest reproducer is fetched using `fetch_url_content()` and stored in a temporary file (`tuxtest_reproducer`).

## 4. Fetching Kernel Information
- The script retrieves related kernel information from the SQUAD API using the `job_url`.
- The kernel URL (`kernel_url`) and other relevant information are extracted from the JSON response.

## 5. Fetching Tuxbuild Configuration
- The script constructs the Tuxbuild configuration URL (`tuxbuild_config_url`) based on the `kernel_url`.
- The content of the Tuxbuild configuration is fetched using `fetch_url_content()` and stored in a temporary file (`tuxbuild_config`).

## 6. Checking for DEBUG_INFO in Kernel
- The script checks if the Tuxbuild configuration contains `CONFIG_DEBUG_INFO=y`.
- If not, indicating that the kernel does not have DEBUG_INFO, the script proceeds to build the kernel with DEBUG_INFO.

## 7. Building Kernel with DEBUG_INFO
- The Tuxbuild reproducer is fetched using `fetch_url_content()` and stored in a temporary file (`tuxbuild_reproducer`).
- The script constructs a new Tuxbuild command with DEBUG_INFO using `get_tuxbuild_cmd_with_debug()`.
- The new Tuxbuild command is executed to build the kernel with DEBUG_INFO.

## 8. Reproducing Test with New Kernel
- The script constructs a new Tuxtest command using `new_test_cmd()` based on the Tuxtest reproducer and Tuxbuild JSON.
- The new Tuxtest command is executed to reproduce the test with the newly built kernel.

## 9. Fetching Tuxtest Logs
- The script fetches the Tuxtest logs URL (`tuxtest_log_url`) based on the Tuxtest download URL.
- The content of the Tuxtest logs is fetched using `fetch_url_content()` and stored in a temporary file (`tuxtest_log`).

## 10. Fetching Debug Artifacts
- The script fetches the vmlinux.xz and System.map URLs from the Tuxbuild using `fetch_url_content()` and stores them in temporary files.
- The vmlinux.xz file is decompressed, and both files (`vmlinux` and `System.map`) are moved to `/tmp/`.

## 11. Decoding Stack Trace
- The script decodes the stack trace from the Tuxtest logs using a Docker container and stores the output in `logs-decoded.txt`.

## 12. Displaying Output
- Throughout the process, the script logs messages using the `log()` function.
- The final decoded stack trace and file locations are displayed as output.

