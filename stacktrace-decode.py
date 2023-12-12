import subprocess
import tempfile
import os
import json
import requests
import re

def log(message):
    print(f"[SD] {message}")

def usage():
    print("Usage: python script.py")
    print("Please provide the SQUAD Testrun URL or SQUAD Test URL when prompted.")

def fetch_url_content(url):
    return requests.get(url).text

def write_content_to_tempfile(content):
    temp_file = tempfile.mktemp()
    with open(temp_file, 'w') as f:
        f.write(content)
    return temp_file

def parse_test_id(url):
    if "https://qa-reports.linaro.org/api/tests/" not in url:
        return None

    plain_test = url.replace("https://qa-reports.linaro.org/api/tests/", "")
    test_id = plain_test.replace("/", "")
    return test_id

def parse_testrun_id(url):
    if "https://qa-reports.linaro.org/api/testruns/" not in url:
        return None

    plain_testrun = url.replace("https://qa-reports.linaro.org/api/testruns/", "")
    testrun_id = plain_testrun.replace("/", "")
    return testrun_id

def is_tuxtest_url(url):
    return bool(re.match(r'^https://tuxapi.tuxsuite.com/v1/groups/[A-Za-z0-9_]*/projects/[A-Za-z0-9_]*/tests/[A-Za-z0-9]*$', url))

def new_test_cmd(tuxsuite_reproducer, tuxbuild_json):
    # Function to construct the new tuxtest command
    tuxtest_cmd = subprocess.check_output(['grep', '^tuxsuite test', tuxsuite_reproducer]).decode().split()
    new_cmd = []

    url_tuxbuild = json.loads(requests.get(tuxbuild_json).text)['download_url']
    kernel_file = json.loads(requests.get(tuxbuild_json).text)['tuxmake_metadata']['results']['artifacts']['kernel'][0]
    modules_file = json.loads(requests.get(tuxbuild_json).text)['tuxmake_metadata']['results']['artifacts']['modules'][0]

    url_kernel = url_tuxbuild + kernel_file
    url_modules = url_tuxbuild + modules_file

    skip = False
    for elem in tuxtest_cmd:
        if skip:
            skip = False
            continue

        if elem == '--kernel':
            skip = True
            new_cmd.extend(['--kernel', url_kernel])
            continue
        elif elem == '--modules':
            skip = True
            new_cmd.extend(['--modules', url_modules])
            continue

        new_cmd.append(elem)

    new_cmd.extend(['--json-out', 'tuxtest.json'])
    return new_cmd

def new_tuxbuild_params(args):
    # Function to process tuxbuild parameters
    new_params = []
    while args:
        arg = args.pop(0)
        if arg.startswith('--'):
            new_params.extend([arg, args.pop(0)])
        elif '=' in arg:
            new_params.append(arg)
        else:
            args.pop(0)

    return new_params

def get_tuxbuild_cmd_from_reproducer(reproducer):
    # Function to get tuxbuild command from reproducer
    tuxsuite_build_cmd = subprocess.check_output(['sed', '-e', 's:# tuxsuite build:tuxsuite build:g', reproducer, '|', 'grep', '^tuxsuite build', '|', 'head', '-n1']).decode().split()
    return tuxsuite_build_cmd

def get_tuxbuild_cmd_with_debug(reproducer, json_out):
    # Function to construct the new tuxbuild command with DEBUG_INFO
    tuxbuild_cmd = get_tuxbuild_cmd_from_reproducer(reproducer)
    new_tuxbuild_cmd = ['tuxsuite', 'build'] + new_tuxbuild_params(tuxbuild_cmd) + ['--kconfig', 'CONFIG_DEBUG_INFO=y', '--kconfig', 'CONFIG_DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT=y', '--json-out', json_out, 'config', 'kernel', 'modules', 'debugkernel']

    return new_tuxbuild_cmd

def build_kernel_and_reproduce_test(tuxbuild_reproducer, tuxtest_reproducer, tuxtest_download_url):
    # Function to build the kernel with DEBUG_INFO and reproduce the test
    tuxbuild_json = tempfile.mktemp()
    new_tuxbuild_cmd = get_tuxbuild_cmd_with_debug(tuxbuild_reproducer, tuxbuild_json)
    subprocess.run(new_tuxbuild_cmd)

    tuxtest_cmd = new_test_cmd(tuxtest_reproducer, tuxbuild_json)
    subprocess.run(tuxtest_cmd, stderr=subprocess.DEVNULL)  # Ignore errors and proceed

def get_tuxtest_logs(tuxtest_download_url):
    # Function to get Tuxtest logs
    tuxtest_log_url = f"{tuxtest_download_url}/logs.txt"
    tuxtest_log = tempfile.mktemp()
    with open(tuxtest_log, 'w') as f:
        f.write(requests.get(tuxtest_log_url).text)

def get_debug_artifacts(tuxbuild_url):
    # Function to get debug artifacts (vmlinux and System.map)
    vmlinuxxz = tempfile.mktemp()
    with open(vmlinuxxz, 'w') as f:
        f.write(requests.get(f"{tuxbuild_url}/vmlinux.xz").content)

    os.rename(vmlinuxxz, '/tmp/vmlinux.xz')
    subprocess.run(['xz', '-df', '/tmp/vmlinux.xz'])

    systemmap_url = f"{tuxbuild_url}/System.map"
    systemmap = tempfile.mktemp()
    with open(systemmap, 'w') as f:
        f.write(requests.get(systemmap_url).text)

    os.rename(systemmap, '/tmp/System.map')
    log("File: vmlinux:          /tmp/vmlinux")
    log("File: System.map:       /tmp/System.map")

def decode_stack_trace(tuxtest_log, vmlinux_path, docker_image):
    # Function to decode the stack trace
    with open(tuxtest_log, 'r') as f:
        subprocess.run(['docker', 'run', '--rm', '-i', '-v', '/data/linux:/linux:ro', '-v', '/tmp:/tmp', docker_image, '/linux/scripts/decode_stacktrace.sh', '/tmp/vmlinux'], stdout=subprocess.PIPE)

def main():
    usage()
    URL = input("Enter SQUAD Testrun URL or SQUAD Test URL: ")
    log(f"URL: {URL}")

    if is_tuxtest_url(URL):
        job_url = URL
    else:
        test_id = parse_test_id(URL)
        if test_id:
            test_json = json.loads(fetch_url_content(URL))
            testrun_url = test_json.get("test_run", "")
            testrun_id = parse_testrun_id(testrun_url)
        else:
            testrun_id = parse_testrun_id(URL)

        if not testrun_id:
            log("ERROR: Could not find SQUAD testrun ID.")
            exit(1)

        log("Getting Tuxtest.")
        testrun_json = json.loads(fetch_url_content(f"https://qa-reports.linaro.org/api/testruns/{testrun_id}/"))
        job_url = testrun_json.get("job_url", "")

    tuxtest_reproducer_url = f"{job_url}/tuxsuite_reproducer"
    tuxtest_reproducer = write_content_to_tempfile(fetch_url_content(tuxtest_reproducer_url))

    log("Getting related kernel information.")
    tuxtest_json = json.loads(fetch_url_content(job_url))
    kernel_url = tuxtest_json.get("kernel", "")
    kernel_basename = os.path.basename(kernel_url)
    tuxbuild_url = kernel_url.replace(f'/{kernel_basename}', '')

    tuxtest_download_url = tuxtest_json.get("download_url", "")

    log("Getting kernel configuration.")
    tuxbuild_config_url = f"{tuxbuild_url}/config"
    tuxbuild_config = write_content_to_tempfile(fetch_url_content(tuxbuild_config_url))

    if "CONFIG_DEBUG_INFO=y" not in open(tuxbuild_config).read():
        log("NOTE: Kernel does not have DEBUG_INFO.")

        log("Getting Tuxbuild reproducer.")
        tuxbuild_reproducer_url = f"{tuxbuild_url}/tuxsuite_reproducer.sh"
        tuxbuild_reproducer = write_content_to_tempfile(fetch_url_content(tuxbuild_reproducer_url))

        build_kernel_and_reproduce_test(tuxbuild_reproducer, tuxtest_reproducer, tuxtest_download_url)

    get_tuxtest_logs(tuxtest_download_url)

    get_debug_artifacts(tuxbuild_url)

    log("Looking for Tuxmake image.")
    aws_image = json.loads(fetch_url_content(tuxbuild_json)).get("tuxmake_metadata", {}).get("runtime", {}).get("image_digest", "")
    docker_image = aws_image.split('.amazonaws.com/')[-1]

    log("Decoding stack trace.")
    decode_stack_trace(tuxtest_log, '/tmp/vmlinux', docker_image)

if __name__ == "__main__":
    main()

