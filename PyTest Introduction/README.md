I Prepare working enenvironment
1. Create a virtual environment in the project root folder
For Windows: Open Command Prompt in your project’s root folder and run:
python -m venv venv
2. Activate the virtual environment
For Windows: In Command Prompt run:
.venv/Scripts/activate.bat
3. Install the latest version of pytest
pip install pytest
4. Install the latest version of pandas
pip install pandas
5. Install the latest version of pytest-html
pip install pytest-html

Note: If you're opening a project DQE-AUTOMATION in VSC for the first time, VSC will immediately ask about creating an environment and installing all libraries from all requirements.txt files. Agree to VSC's suggestions.

If something goes wrong, follow the instructions above.

II. Command for running tests
python -m pytest "D:\DQE\dqe-automation\PyTest Introduction\tests\test_csv\test_csv.py" --csv-path="D:\DQE\dqe-automation\PyTest Introduction\src\data\data.csv"

"D:\DQE\dqe-automation\PyTest Introduction\tests\test_csv\test_csv.py" - change to your path to the pytest file location

--csv-path="D:\DQE\dqe-automation\PyTest Introduction\src\data\data.csv" - change to your path to the data.csv file location

III. Command for creating reports
all tests:
python -m pytest "D:\DQE\dqe-automation\PyTest Introduction\tests\test_csv\test_csv.py" --csv-path="D:\DQE\dqe-automation\PyTest Introduction\src\data\data.csv"

unmarked tests:
python -m pytest "D:\DQE\dqe-automation\PyTest Introduction\tests\test_csv\test_csv.py" --csv-path="D:\DQE\dqe-automation\PyTest Introduction\src\data\data.csv" -m unmarked

validate_csv and not xfail tests:
python -m pytest "D:\DQE\dqe-automation\PyTest Introduction\tests\test_csv\test_csv.py" --csv-path="D:\DQE\dqe-automation\PyTest Introduction\src\data\data.csv" -m "validate_csv and not xfail"
