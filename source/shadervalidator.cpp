//-zw

// I built this with the Windows Desktop Application template, should just be a drop-in-replacement of the main source file.

#include "framework.h"
#include "name-of-your-vs-project.h"
#include <stdio.h>
#include <iostream>
#include <vector>
#include <shobjidl_core.h>

// DirectX 9
// Requires you to run this command in Visual Studio's NuGet console:
// NuGet\Install-Package Microsoft.DXSDK.D3DX -Version 9.29.952.8
#include <d3d9.h>
#include "d3dx9.h"
#include "D3DX9Effect.h"



typedef void (*vfptr)();

char* shader = NULL;
char* currentFilename = NULL;
unsigned long long shaderLength = 0;
char* errs = 0;
unsigned long long errsize = 0;
HWND g_hWnd = NULL;
HWND buttons[50];
vfptr OnClicks[50];
int buttonsLength = 0;

int windowX = 500;
int windowY = 500;

void CreateSHA();

#define MAX_LOADSTRING 100

// Global Variables:
HINSTANCE hInst;                                // current instance
WCHAR szTitle[MAX_LOADSTRING];                  // The title bar text
WCHAR szWindowClass[MAX_LOADSTRING];            // the main window class name

// Forward declarations of functions included in this code module:
ATOM                MyRegisterClass(HINSTANCE hInstance);
BOOL                InitInstance(HINSTANCE, int);
LRESULT CALLBACK    WndProc(HWND, UINT, WPARAM, LPARAM);
INT_PTR CALLBACK    About(HWND, UINT, WPARAM, LPARAM);

int APIENTRY wWinMain(_In_ HINSTANCE hInstance,
    _In_opt_ HINSTANCE hPrevInstance,
    _In_ LPWSTR    lpCmdLine,
    _In_ int       nCmdShow)
{
    UNREFERENCED_PARAMETER(hPrevInstance);
    UNREFERENCED_PARAMETER(lpCmdLine);

    // TODO: Place code here.

    // Initialize global strings
    LoadStringW(hInstance, IDS_APP_TITLE, szTitle, MAX_LOADSTRING);
    LoadStringW(hInstance, IDC_DIRECTX9, szWindowClass, MAX_LOADSTRING);
    MyRegisterClass(hInstance);

    // Perform application initialization:
    if (!InitInstance(hInstance, nCmdShow))
    {
        return FALSE;
    }

    HACCEL hAccelTable = LoadAccelerators(hInstance, MAKEINTRESOURCE(IDC_DIRECTX9));

    MSG msg;

    // Main message loop:
    while (GetMessage(&msg, nullptr, 0, 0))
    {
        if (!TranslateAccelerator(msg.hwnd, hAccelTable, &msg))
        {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }
    }

    return (int)msg.wParam;
}





//
//  FUNCTION: MyRegisterClass()
//
//  PURPOSE: Registers the window class.
//
ATOM MyRegisterClass(HINSTANCE hInstance)
{
    WNDCLASSEXW wcex;

    wcex.cbSize = sizeof(WNDCLASSEX);

    wcex.style = CS_HREDRAW | CS_VREDRAW;
    wcex.lpfnWndProc = WndProc;
    wcex.cbClsExtra = 0;
    wcex.cbWndExtra = 0;
    wcex.hInstance = hInstance;
    wcex.hIcon = LoadIcon(hInstance, MAKEINTRESOURCE(IDI_DIRECTX9));
    wcex.hCursor = LoadCursor(nullptr, IDC_ARROW);
    wcex.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wcex.lpszMenuName = NULL;// MAKEINTRESOURCEW(IDC_DIRECTX9);
    wcex.lpszClassName = szWindowClass;
    wcex.hIconSm = LoadIcon(wcex.hInstance, MAKEINTRESOURCE(IDI_SMALL));

    return RegisterClassExW(&wcex);
}

LPDIRECT3D9 g_pD3D = NULL;
LPDIRECT3DDEVICE9 d3dDevice = NULL;

static BOOL InitD3D(HWND hWnd)
{
    if ((g_pD3D = Direct3DCreate9(D3D_SDK_VERSION)) == NULL) return FALSE;

    D3DPRESENT_PARAMETERS d3dpp;

    ZeroMemory(&d3dpp, sizeof(d3dpp));
    d3dpp.Windowed = TRUE;
    d3dpp.SwapEffect = D3DSWAPEFFECT_COPY;

    if (FAILED(g_pD3D->CreateDevice(D3DADAPTER_DEFAULT, D3DDEVTYPE_HAL, hWnd,
        D3DCREATE_SOFTWARE_VERTEXPROCESSING,
        &d3dpp, &d3dDevice)))
        return FALSE;

    return TRUE;
}

#define ErrorBox(message, caption) MessageBoxA(g_hWnd, message, caption, MB_ICONERROR)


PWSTR AskOpenFilename()
{
    IFileOpenDialog* pFileOpen;
    // Create the FileOpenDialog object.
    HRESULT hr = CoCreateInstance(CLSID_FileOpenDialog, NULL, CLSCTX_ALL, IID_IFileOpenDialog, reinterpret_cast<void**>(&pFileOpen));
    if (SUCCEEDED(hr))
    {
        hr = pFileOpen->Show(NULL);
        if (SUCCEEDED(hr))
        {
            IShellItem* pItem;
            hr = pFileOpen->GetResult(&pItem);
            if (SUCCEEDED(hr))
            {
                PWSTR pszFilePath;
                hr = pItem->GetDisplayName(SIGDN_FILESYSPATH, &pszFilePath);
                return pszFilePath;
            }
        }
    }
    return NULL;
}


//////////////////////////////////////////////////
// Button system because the Windows API is confusing
//////////////////////////////////////////////////
void CreateButton(HWND hWnd, const wchar_t* text, int x, int y, int width, int height, vfptr function)
{
    buttons[buttonsLength] = CreateWindowW(L"BUTTON", text, WS_TABSTOP | WS_VISIBLE | WS_CHILD | BS_DEFPUSHBUTTON, x, y, width, height, hWnd, NULL, (HINSTANCE)GetWindowLongPtr(hWnd, GWLP_HINSTANCE), NULL);
    OnClicks[buttonsLength] = function;
    buttonsLength++;
}

int GetButtonIndex(HWND hButton)
{
    for (int i = 0; i < buttonsLength; i++)
    {
        if (buttons[i] == hButton) return i;
    }
    return -1;
}


static HANDLE winOpen(const char* filename, const char* mode)
{
    UINT shareMode = FILE_SHARE_READ;
    UINT access = GENERIC_READ;
    UINT open = OPEN_EXISTING;
    if (*mode == 'w')
    {
        shareMode = FILE_SHARE_WRITE;
        access = GENERIC_WRITE;
        open = OPEN_ALWAYS;
    }

    return CreateFileA(filename, access, shareMode, NULL, open, FILE_ATTRIBUTE_NORMAL, NULL);
}

#define CloseFile(a) CloseHandle(a)


static void OpenShader(const wchar_t* filename)
{
    if (shader)
    {
        free(shader);
        shader = NULL;
    }
    // Why does Microsoft's fopen have to be so complicated?
    HANDLE hFile = CreateFileW(filename, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);

    DWORD high;
    DWORD low = GetFileSize(hFile, &high);
    unsigned long long fullresult = ((unsigned long long)high << 32) | low;
    shaderLength = fullresult;
    shader = (char*)malloc(fullresult);
    if (shader == NULL)
    {
        ErrorBox("Out of memory, can't read shader!", "Initialization Error");
        return;
    }

    DWORD bytesRead;

    if (!ReadFile(hFile, shader, fullresult, &bytesRead, NULL))
    {
        ErrorBox("Can't read file (is it being used by another process?)", "Initialization Error");
        return;
    }

    CloseHandle(hFile);
}

static void CheckForErrors()
{
    PWSTR filename = AskOpenFilename();
    if (!filename) return;

    OpenShader(filename);

    LPD3DXEFFECT pEffect;
    LPD3DXBUFFER errors;
    D3DXCreateEffect(d3dDevice, shader, shaderLength, NULL, NULL, 0, NULL, &pEffect, &errors);

    UINT messageType = MB_ICONINFORMATION;
    if (errors)
    {
        messageType = MB_ICONERROR;
        errs = (char*)errors->GetBufferPointer();
        errsize = errors->GetBufferSize();
    }
    else
    {
        errs = (char*)"No errors, yay!";
        errsize = 15;
    }

    MessageBoxA(g_hWnd, errs, "Result:", messageType);
}

static void CreateUIElements(HWND hWnd)
{
    CreateButton(hWnd, L"Validate SHA", 0, 300, 500, 100, CheckForErrors);
}



//
//   FUNCTION: InitInstance(HINSTANCE, int)
//
//   PURPOSE: Saves instance handle and creates main window
//
//   COMMENTS:
//
//        In this function, we save the instance handle in a global variable and
//        create and display the main program window.
//
BOOL InitInstance(HINSTANCE hInstance, int nCmdShow)
{
    hInst = hInstance; // Store instance handle in our global variable

    HWND hWnd = CreateWindowW(szWindowClass, szTitle, WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT, 0, windowX, windowY, nullptr, nullptr, hInstance, nullptr);

    if (!hWnd)
    {
        return FALSE;
    }

    g_hWnd = hWnd;


    if (!InitD3D(hWnd))
    {
        ErrorBox("Failed to initialize Direct X", "Initialization Error");
        return FALSE;
    }

    CreateUIElements(hWnd);

    ShowWindow(hWnd, nCmdShow);
    UpdateWindow(hWnd);

    return TRUE;
}

//
//  FUNCTION: WndProc(HWND, UINT, WPARAM, LPARAM)
//
//  PURPOSE: Processes messages for the main window.
//
//  WM_COMMAND  - process the application menu
//  WM_PAINT    - Paint the main window
//  WM_DESTROY  - post a quit message and return
//
//
LRESULT CALLBACK WndProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam)
{
    switch (message)
    {
    case WM_COMMAND:
    {
        int notif = HIWORD(wParam);
        int dex;
        switch (notif)
        {
        case BN_CLICKED:
            dex = GetButtonIndex((HWND)lParam);
            if (dex != -1)
                OnClicks[dex]();
            break;
        default:
            int wmId = LOWORD(wParam);
            // Parse the menu selections:
            switch (wmId)
            {
            case IDM_ABOUT:
                DialogBox(hInst, MAKEINTRESOURCE(IDD_ABOUTBOX), hWnd, About);
                break;
            case IDM_EXIT:
                DestroyWindow(hWnd);
                break;

            default:
                return DefWindowProc(hWnd, message, wParam, lParam);
            }
        }

    }
    break;
    case WM_PAINT:
    {
        PAINTSTRUCT ps;
        HBRUSH hBrush = CreateSolidBrush(RGB(10, 10, 10));
        RECT rect = { 0, 0, 400, 400 };
        RECT titleRect = { 0, 0, 500, 100 };
        RECT descRect = { 0, 50, 500, 100 };
        RECT disclaimerRect = { 0, 100, 500, 150 };
        GetClientRect(hWnd, &rect);
        HDC hdc = BeginPaint(hWnd, &ps);



        DrawTextA(hdc, "Zack's FlatOut Shader Validator", 32, &titleRect, DT_CENTER);
        DrawTextA(hdc, "This app compiles the SHA just like the game,\nexcept it will show you the errors.", 82, &descRect, DT_CENTER);
        DrawTextA(hdc, "Ignore the visuals, I wrote this GUI in C++", 44, &disclaimerRect, DT_CENTER);

        EndPaint(hWnd, &ps);
    }
    break;

    case WM_DESTROY:
        free(shader);
        PostQuitMessage(0);
        break;
    default:
        return DefWindowProc(hWnd, message, wParam, lParam);
    }
    return 0;
}

// Message handler for about box.
INT_PTR CALLBACK About(HWND hDlg, UINT message, WPARAM wParam, LPARAM lParam)
{
    UNREFERENCED_PARAMETER(lParam);
    switch (message)
    {
    case WM_INITDIALOG:
        return (INT_PTR)TRUE;

    case WM_COMMAND:
        if (LOWORD(wParam) == IDOK || LOWORD(wParam) == IDCANCEL)
        {
            EndDialog(hDlg, LOWORD(wParam));
            return (INT_PTR)TRUE;
        }
        break;
    }
    return (INT_PTR)FALSE;
}
