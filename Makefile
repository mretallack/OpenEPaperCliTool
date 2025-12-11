
PYTHON=python3.12

send: venv/bin/activate
	. venv/bin/activate && cd clitool && ${PYTHON} -m eink_cli.cli send test_device.yaml -t 30

discover: venv/bin/activate
	. venv/bin/activate && cd clitool && ${PYTHON} -m eink_cli.cli discover

venv/bin/activate: clitool/requirements.txt
	${PYTHON} -m venv venv
	. venv/bin/activate && ${PYTHON} -m pip install -r clitool/requirements.txt

