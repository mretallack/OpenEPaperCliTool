
PYTHON=python3.12

send: venv/bin/activate
	. venv/bin/activate && cd clitool && ${PYTHON} -m eink_cli.cli send test_device.yaml -t 30

discover: venv/bin/activate
	. venv/bin/activate && cd clitool && ${PYTHON} -m eink_cli.cli discover

runcontroller: venv/bin/activate
	. venv/bin/activate && cd controller && ${PYTHON} mqtt_controller.py


runtest: venv/bin/activate
	. venv/bin/activate && cd controller && ${PYTHON} test_publisher.py


venv/bin/activate: clitool/requirements.txt controller/requirements.txt
	${PYTHON} -m venv venv
	. venv/bin/activate && ${PYTHON} -m pip install -r clitool/requirements.txt
	. venv/bin/activate && ${PYTHON} -m pip install -r controller/requirements.txt


