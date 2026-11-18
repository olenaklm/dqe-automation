*** Settings ***
Library           SeleniumLibrary
Library           helper.py
Suite Teardown    Close All Browsers


*** Variables ***
${REPORT_FILE}       ${CURDIR}${/}report.html
${PARQUET_FOLDER}    ${CURDIR}${/}parquet_data
${FILTER_DATE}       2025-06-19
${BROWSER}           chrome
${TIMEOUT}           15 seconds


*** Test Cases ***
HTML Report Table Should Match Aggregated Parquet Data
    [Documentation]    Verifies that the HTML report table matches the Parquet dataset.

    ${report_url}=    Get File Uri    ${REPORT_FILE}

    Open Browser    ${report_url}    ${BROWSER}
    Set Selenium Timeout    ${TIMEOUT}
    Maximize Browser Window

    Wait Until Element Is Visible    css:.table    ${TIMEOUT}
    ${table}=    Get WebElement    css:.table

    ${html_dataframe}=    Read Html Table Data    ${table}

    ${parquet_dataframe}=    Read Partitioned Parquet Dataset
    ...    ${PARQUET_FOLDER}
    ...    ${FILTER_DATE}

    ${differences}=    Compare Dataframes Exactly
    ...    ${html_dataframe}
    ...    ${parquet_dataframe}

    Should Be Empty
    ...    ${differences}
    ...    msg=HTML report table and Parquet dataset do not match:${\n}${differences}