// Savage Wind VR.exe (Windows, `make dist VR=1`): starts the runtime from its own folder with the VR mode on
// (SAVAGEWIND_VR=1; docs/VR.md). Any SAVAGEWIND_VR* variable already set wins. Its arguments go to the game. The VR
// options themselves are on the game's Options screen (VR page).
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

static BOOL write_start_failure(const wchar_t *path, const wchar_t *launcher, const wchar_t *runtime, DWORD error) {
    SYSTEMTIME now;
    GetLocalTime(&now);
    wchar_t system[512] = L"Unknown Windows error";
    FormatMessageW(FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS, NULL, error, 0, system,
                   sizeof system / sizeof *system, NULL);
    wchar_t entry[2048];
    int chars = swprintf(entry, sizeof entry / sizeof *entry,
                         L"[%04u-%02u-%02u %02u:%02u:%02u] Savage Wind VR launcher failed\n"
                         L"Launcher: %ls\nRuntime: %ls\nWindows error: %lu (%ls)\n\n",
                         now.wYear, now.wMonth, now.wDay, now.wHour, now.wMinute, now.wSecond,
                         launcher, runtime, error, system);
    if (chars <= 0 || (size_t)chars >= sizeof entry / sizeof *entry) return FALSE;
    int bytes = WideCharToMultiByte(CP_UTF8, 0, entry, chars, NULL, 0, NULL, NULL);
    if (bytes <= 0) return FALSE;
    char utf8[8192];
    if (bytes >= (int)sizeof utf8 || !WideCharToMultiByte(CP_UTF8, 0, entry, chars, utf8, sizeof utf8, NULL, NULL))
        return FALSE;
    HANDLE file = CreateFileW(path, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_ALWAYS,
                              FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return FALSE;
    DWORD written = 0;
    BOOL ok = WriteFile(file, utf8, (DWORD)bytes, &written, NULL) && written == (DWORD)bytes;
    CloseHandle(file);
    return ok;
}

int WINAPI wWinMain(HINSTANCE inst, HINSTANCE prev, PWSTR args, int show) {
    (void)inst, (void)prev, (void)show;
    if (!GetEnvironmentVariableW(L"SAVAGEWIND_VR", NULL, 0)) SetEnvironmentVariableW(L"SAVAGEWIND_VR", L"1");
    wchar_t launcher[MAX_PATH], dir[MAX_PATH], exe[MAX_PATH + 32], cmd[MAX_PATH + 32 + 4096];
    DWORD ln = GetModuleFileNameW(NULL, launcher, MAX_PATH);
    if (!ln || ln >= MAX_PATH) return 1;
    DWORD n = GetModuleFileNameW(NULL, dir, MAX_PATH);
    if (!n || n >= MAX_PATH) return 1;
    wchar_t *slash = wcsrchr(dir, L'\\');
    if (slash) *slash = 0;
    wchar_t log[MAX_PATH + 40], previous_log[MAX_PATH + 48];
    swprintf(log, sizeof log / sizeof *log, L"%ls\\savagewind-launcher.log", dir);
    swprintf(previous_log, sizeof previous_log / sizeof *previous_log, L"%ls\\savagewind-launcher.prev.log", dir);
    MoveFileExW(log, previous_log, MOVEFILE_REPLACE_EXISTING);
#ifdef SW_VR_MAKER
    swprintf(exe, sizeof exe / sizeof *exe, L"%ls\\savagewind-vr-runtime.exe", dir);
#else
    swprintf(exe, sizeof exe / sizeof *exe, L"%ls\\savagewind.exe", dir);
#endif
    swprintf(cmd, sizeof cmd / sizeof *cmd, L"\"%ls\" %ls", exe, args ? args : L"");
    STARTUPINFOW si = {0};
    si.cb = sizeof si;
    si.hStdInput = GetStdHandle(STD_INPUT_HANDLE), si.hStdOutput = GetStdHandle(STD_OUTPUT_HANDLE);
    si.hStdError = GetStdHandle(STD_ERROR_HANDLE);
    if (si.hStdOutput || si.hStdError) si.dwFlags |= STARTF_USESTDHANDLES;  // (started with them: a log, a test)
    PROCESS_INFORMATION pi;
    if (!CreateProcessW(exe, cmd, NULL, NULL, TRUE, 0, NULL, dir, &si, &pi)) {  // (handles inherited: its output too)
        DWORD error = GetLastError();
        wchar_t text[1800], system[512] = L"Unknown Windows error";
        FormatMessageW(FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS, NULL, error, 0, system,
                       sizeof system / sizeof *system, NULL);
        BOOL runtime_exists = GetFileAttributesW(exe) != INVALID_FILE_ATTRIBUTES;
        BOOL logged = write_start_failure(log, launcher, exe, error);
        const wchar_t *log_hint = logged ? log : L"(the diagnostic log could not be written)";
#ifdef SW_VR_MAKER
        const wchar_t *missing = L"savagewind-vr-runtime.exe";
#else
        const wchar_t *missing = L"savagewind.exe";
#endif
        if (!runtime_exists)
            swprintf(text, sizeof text / sizeof *text,
                     L"Savage Wind VR could not start: %ls is missing next to the launcher.\n\n"
                     L"Extract the complete VR package again. Details: %ls",
                     missing, log_hint);
        else
            swprintf(text, sizeof text / sizeof *text,
                     L"Savage Wind VR could not start. Windows reported error %lu: %ls\n\n"
                     L"A runtime DLL may be missing or blocked by antivirus. Extract the complete VR package again "
                     L"and check your antivirus. Details: %ls",
                     error, system, log_hint);
        MessageBoxW(NULL, text, L"Savage Wind VR", MB_ICONERROR | MB_OK);
        return 1;
    }
    // (waits for the game: whatever started this one - Steam, a shortcut, a test - sees the game's run and exit code)
    CloseHandle(pi.hThread);
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD code = 0;
    GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hProcess);
    return (int)code;
}
