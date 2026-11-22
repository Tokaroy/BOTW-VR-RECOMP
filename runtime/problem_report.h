// A problem report (runtime/problem_report.c): Options > Problem report, and the start screen's Prelaunch tab.
#pragma once

#ifdef __cplusplus
extern "C" {
#endif
// Makes problem-report-<date>-<time>.zip in the data folder with current and previous runtime/launcher logs, settings,
// pipeline lists and system.txt. No game files, no saves, nothing sent anywhere. Returns the file's name, "" if it
// couldn't be made.
const char *problem_report_make(void);
#ifdef __cplusplus
}
#endif
