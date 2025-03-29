//-zw

// I built this with the Windows Desktop Application template
// It's based on the project name so there's a bunch of PROJECT_NAME_HEREs that you'll need to replace
// but other than that it should just be a drop-in-replacement of the main source file, and running the nuget command to download the SDK

#include "framework.h"
#include "PROJECT_NAME_HERE.h"
#include <stdio.h>
#include <iostream>
#include <vector>
#include <shobjidl_core.h>

// DirectX 9
// Requires you to run this command in Visual Studio's NuGet console:
// NuGet\Install-Package Microsoft.DXSDK.D3DX -Version 9.29.952.8
#include <d3d9.h>
#include "../packages\Microsoft.DXSDK.D3DX.9.29.952.8\build\native\include\d3dx9.h"
#include "../packages\Microsoft.DXSDK.D3DX.9.29.952.8\build\native\include\D3DX9Effect.h"

#define CloseFile(a) CloseHandle(a)
#define RELEASE(x) if (x) x->Release(); x = NULL

constexpr float FAR_CLIP = 1500.f;
constexpr float CAMERA_DISTANCE = 2.5f;

typedef void (*vfptr)();

char* shader = NULL;
PWSTR currentFilename = NULL;
unsigned long long shaderLength = 0;
char* errs = 0;
unsigned long long errsize = 0;
HWND g_hWnd = NULL;
HWND buttons[50];
vfptr OnClicks[50];
int buttonsLength = 0;
time_t testmtime = 0;

LPDIRECT3D9 g_pD3D = NULL;
LPDIRECT3DDEVICE9 d3dDevice = NULL;

LPD3DXEFFECT pEffect = NULL;
LPDIRECT3DTEXTURE9 pBaseColour = NULL;
LPDIRECT3DTEXTURE9 pDirt = NULL;
LPDIRECT3DCUBETEXTURE9 pSpecular = NULL;
LPDIRECT3DCUBETEXTURE9 pLighting = NULL;
D3DMATERIAL9 mat;
LPD3DXMESH pMesh = NULL;

int windowX = 1024;
int windowY = 500;

void Render(RECT* rect);
PWSTR AskOpenFilename();
void OpenShader(const wchar_t* filename);
void CheckForErrors(PWSTR filename, bool showSuccess);
void ChangeMesh(const wchar_t* filename);

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
	LoadStringW(hInstance, IDC_PROJECT_NAME_HERE, szWindowClass, MAX_LOADSTRING);
	MyRegisterClass(hInstance);

	// Perform application initialization:
	if (!InitInstance(hInstance, nCmdShow))
	{
		return FALSE;
	}

	HACCEL hAccelTable = LoadAccelerators(hInstance, MAKEINTRESOURCE(IDC_PROJECT_NAME_HERE));

	MSG msg;
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
	wcex.hIcon = LoadIcon(hInstance, MAKEINTRESOURCE(IDI_PROJECT_NAME_HERE));
	wcex.hCursor = LoadCursor(nullptr, IDC_ARROW);
	wcex.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
	wcex.lpszMenuName = NULL;// MAKEINTRESOURCEW(IDC_PROJECT_NAME_HERE);
	wcex.lpszClassName = szWindowClass;
	wcex.hIconSm = LoadIcon(wcex.hInstance, MAKEINTRESOURCE(IDI_SMALL));

	return RegisterClassExW(&wcex);
}

#define ErrorBox(message, caption) MessageBoxA(g_hWnd, message, caption, MB_ICONERROR)

char printfbuffer[1024];

void PrintF(const char* format, ...)
{
	va_list list;
	va_start(list, format);

	vsprintf_s(printfbuffer, format, list);
	ErrorBox(printfbuffer, "");
}

char convertBuffer[256];


void PrintD3DError(HRESULT hr, const char* warning)
{
	const char* message = "This error needs to be added to the list so it can be printed.";

	switch (hr)
	{
	case D3D_OK:
		message = "D3D_OK";
		break;

	case D3DERR_WRONGTEXTUREFORMAT:
		message = "D3DERR_WRONGTEXTUREFORMAT";
		break;

	case D3DERR_UNSUPPORTEDCOLOROPERATION:
		message = "D3DERR_UNSUPPORTEDCOLOROPERATION";
		break;

	case D3DERR_UNSUPPORTEDCOLORARG:
		message = "D3DERR_UNSUPPORTEDCOLORARG";
		break;

	case D3DERR_UNSUPPORTEDALPHAOPERATION:
		message = "D3DERR_UNSUPPORTEDALPHAOPERATION";
		break;

	case D3DERR_UNSUPPORTEDALPHAARG:
		message = "D3DERR_UNSUPPORTEDALPHAARG";
		break;

	case D3DERR_TOOMANYOPERATIONS:
		message = "D3DERR_TOOMANYOPERATIONS";
		break;

	case D3DERR_CONFLICTINGTEXTUREFILTER:
		message = "D3DERR_CONFLICTINGTEXTUREFILTER";
		break;

	case D3DERR_UNSUPPORTEDFACTORVALUE:
		message = "D3DERR_UNSUPPORTEDFACTORVALUE";
		break;

	case D3DERR_CONFLICTINGRENDERSTATE:
		message = "D3DERR_CONFLICTINGRENDERSTATE";
		break;

	case D3DERR_UNSUPPORTEDTEXTUREFILTER:
		message = "D3DERR_UNSUPPORTEDTEXTUREFILTER";
		break;

	case D3DERR_CONFLICTINGTEXTUREPALETTE:
		message = "D3DERR_CONFLICTINGTEXTUREPALETTE";
		break;

	case D3DERR_DRIVERINTERNALERROR:
		message = "D3DERR_DRIVERINTERNALERROR";
		break;

	case D3DERR_NOTFOUND:
		message = "D3DERR_NOTFOUND";
		break;

	case D3DERR_MOREDATA:
		message = "D3DERR_MOREDATA";
		break;

	case D3DERR_DEVICELOST:
		message = "D3DERR_DEVICELOST";
		break;

	case D3DERR_DEVICENOTRESET:
		message = "D3DERR_DEVICENOTRESET";
		break;

	case D3DERR_NOTAVAILABLE:
		message = "D3DERR_NOTAVAILABLE";
		break;

	case E_OUTOFMEMORY:
		message = "E_OUTOFMEMORY";
		break;

	case D3DERR_OUTOFVIDEOMEMORY:
		message = "D3DERR_OUTOFVIDEOMEMORY";
		break;

	case D3DERR_INVALIDDEVICE:
		message = "D3DERR_INVALIDDEVICE";
		break;

	case D3DERR_INVALIDCALL:
		message = "D3DERR_INVALIDCALL";
		break;

	case D3DXERR_INVALIDDATA:
		message = "D3DXERR_INVALIDDATA";
		break;

	case D3DERR_DRIVERINVALIDCALL:
		message = "D3DERR_DRIVERINVALIDCALL";
		break;

	case D3DERR_WASSTILLDRAWING:
		message = "D3DERR_WASSTILLDRAWING";
		break;

	case D3DERR_DEVICEREMOVED:
		message = "D3DERR_DEVICEREMOVED";
		break;

	case D3DERR_DEVICEHUNG:
		message = "D3DERR_DEVICEHUNG";
		break;

	case D3DERR_UNSUPPORTEDOVERLAY:
		message = "D3DERR_UNSUPPORTEDOVERLAY";
		break;

	case D3DERR_UNSUPPORTEDOVERLAYFORMAT:
		message = "D3DERR_UNSUPPORTEDOVERLAYFORMAT";
		break;

	case D3DERR_CANNOTPROTECTCONTENT:
		message = "D3DERR_CANNOTPROTECTCONTENT";
		break;

	case D3DERR_UNSUPPORTEDCRYPTO:
		message = "D3DERR_UNSUPPORTEDCRYPTO";
		break;

	case D3DERR_PRESENT_STATISTICS_DISJOINT:
		message = "D3DERR_PRESENT_STATISTICS_DISJOINT";
		break;
	case E_FAIL:
		message = "E_FAIL";
		break;
	case E_INVALIDARG:
		message = "E_INVALIDARG";
		break;
	case RPC_E_WRONG_THREAD:
		message = "RPC_E_WRONG_THREAD";
		break;
	default:
		_ltoa_s(hr, convertBuffer, 16);
		message = convertBuffer;
		break;
	}

	PrintF(warning, message);
}

static void check(HRESULT hr, const char* message)
{
	if (FAILED(hr))
		PrintD3DError(hr, message);
}




bool stopRendering = false;



static void DeInitD3D()
{
	RELEASE(pMesh);
	RELEASE(pBaseColour);
	RELEASE(pSpecular);
	RELEASE(pDirt);
	RELEASE(pLighting);

	RELEASE(pEffect);
	RELEASE(d3dDevice);
	RELEASE(g_pD3D);
}

D3DXVECTOR3 lightDir = {
	0.0f, 0.7f, 0.7f
};

static void FillLightingCubemap(D3DXVECTOR4* pOut, const D3DXVECTOR3* pTexCoord, const D3DXVECTOR3* pTexelSize, LPVOID pData)
{
	FLOAT brightness = D3DXVec3Dot(pTexCoord, &lightDir);
	pOut->x = pOut->y = pOut->z = 0.0f;
	pOut->w = brightness;
}

static void LoadImageOnCubemap(D3DCUBEMAP_FACES face, const wchar_t* filename, IDirect3DCubeTexture9* cubemap)
{
	IDirect3DSurface9* surface;
	cubemap->GetCubeMapSurface(face, 0, &surface);
	D3DXIMAGE_INFO info;
	D3DXLoadSurfaceFromFileW(surface, NULL, NULL, filename, NULL, D3DX_DEFAULT, 0, &info);
}

// Basically it'll try to emulate the arrangement of textures and constants to match a specific shader
enum EFFECTCONTEXT
{
	CXT_CAR,
	CXT_WATER,
	CXT_POST,
};

EFFECTCONTEXT context = CXT_CAR;

static void LoadTextures()
{
	RELEASE(pBaseColour);
	RELEASE(pSpecular);
	RELEASE(pDirt);
	RELEASE(pLighting);

	switch (context)
	{
	case CXT_WATER:
		break;
	case CXT_POST:
		break;
	default:
		check(D3DXCreateTextureFromFileExW(d3dDevice, L"colour.png", 0, 0, 0, 0, D3DFMT_UNKNOWN, D3DPOOL_DEFAULT, D3DX_DEFAULT, D3DX_DEFAULT, 0, NULL, NULL, &pBaseColour), "Failed to create colour texture: %s");
		check(D3DXCreateCubeTexture(d3dDevice, 512, 1, 0, D3DFMT_UNKNOWN, D3DPOOL_DEFAULT, &pSpecular), "Failed to create lighting texure: %s");

		// I have no idea how bugbear took 6 separate textures and combined them into a cubemap,
		// because this method causes some of the textures to be oriented the wrong way. I had to edit the images to compensate
		LoadImageOnCubemap(D3DCUBEMAP_FACE_POSITIVE_X, L"arena_day_ft.tga", pSpecular);
		LoadImageOnCubemap(D3DCUBEMAP_FACE_POSITIVE_Y, L"arena_day_lf.tga", pSpecular);
		LoadImageOnCubemap(D3DCUBEMAP_FACE_POSITIVE_Z, L"arena_day_up.tga", pSpecular);
		LoadImageOnCubemap(D3DCUBEMAP_FACE_NEGATIVE_X, L"arena_day_bk.tga", pSpecular);
		LoadImageOnCubemap(D3DCUBEMAP_FACE_NEGATIVE_Y, L"arena_day_rt.tga", pSpecular);
		LoadImageOnCubemap(D3DCUBEMAP_FACE_NEGATIVE_Z, L"arena_day_dn.tga", pSpecular);

		//check(D3DXCreateCubeTextureFromFileA(d3dDevice, "arena_day_bk.tga", &pSpecular), "Failed to create specular texure: %s");
		check(D3DXCreateTextureFromFileA(d3dDevice, "dirt.png", &pDirt), "Failed to create dirt texure: %s");

		check(D3DXCreateCubeTexture(d3dDevice, 512, 0, 0, D3DFMT_UNKNOWN, D3DPOOL_DEFAULT, &pLighting), "Failed to create lighting texure: %s");
		check(D3DXFillCubeTexture(pLighting, FillLightingCubemap, NULL), "Failed to fill lighting texure: %s");
		break;
	}
}

static BOOL InitD3D(HWND hWnd)
{
	if ((g_pD3D = Direct3DCreate9(D3D_SDK_VERSION)) == NULL)
	{
		ErrorBox("Failed to Direct3DCreate9()", "Initialization Error");
		return FALSE;
	}

	D3DPRESENT_PARAMETERS d3dpp;

	ZeroMemory(&d3dpp, sizeof(d3dpp));
	d3dpp.Windowed = TRUE;
	d3dpp.SwapEffect = D3DSWAPEFFECT_DISCARD;
	d3dpp.hDeviceWindow = hWnd;
	d3dpp.BackBufferWidth = 500;
	d3dpp.BackBufferHeight = 500;
	d3dpp.EnableAutoDepthStencil = TRUE;
	d3dpp.AutoDepthStencilFormat = D3DFMT_D16;

	if (FAILED(g_pD3D->CreateDevice(D3DADAPTER_DEFAULT, D3DDEVTYPE_HAL, hWnd,
		D3DCREATE_HARDWARE_VERTEXPROCESSING,
		&d3dpp, &d3dDevice)))
	{
		DeInitD3D();
		ErrorBox("Failed to CreateDevice()", "Initialization Error");
		return FALSE;
	}

	return TRUE;
}




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
				if (SUCCEEDED(hr))
					return pszFilePath;
			}
		}
	}

	PrintD3DError(hr, "Failed to open file: %s");
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

static HANDLE winopen(const char* filename, char mode)
{
	UINT shareMode = FILE_SHARE_READ;
	UINT access = GENERIC_READ;
	UINT open = OPEN_EXISTING;
	if (mode == 'w')
	{
		shareMode = FILE_SHARE_WRITE;
		access = GENERIC_WRITE;
		open = OPEN_ALWAYS;
	}

	return CreateFileA(filename, access, shareMode, NULL, open, FILE_ATTRIBUTE_NORMAL, NULL);
}

static HANDLE winopen(const wchar_t* filename, wchar_t mode)
{
	UINT shareMode = FILE_SHARE_READ;
	UINT access = GENERIC_READ;
	UINT open = OPEN_EXISTING;
	if (mode == L'w')
	{
		shareMode = FILE_SHARE_WRITE;
		access = GENERIC_WRITE;
		open = OPEN_ALWAYS;
	}

	return CreateFileW(filename, access, shareMode, NULL, open, FILE_ATTRIBUTE_NORMAL, NULL);
}



// The resulting pointer will need to be freed afterwards
static char* winread(HANDLE hFile, unsigned long long* out_length)
{
	DWORD high;
	DWORD low = GetFileSize(hFile, &high);
	unsigned long long fullresult = ((unsigned long long)high << 32) | low;
	if (out_length)
		*out_length = fullresult;
	char* block = (char*)malloc(fullresult);
	if (block)
	{
		if (!ReadFile(hFile, block, fullresult, &high, NULL))
		{
			free(block);
			block = NULL;
		}
	}
	return block;
}


static void OpenShader(const wchar_t* filename)
{
	if (shader)
	{
		free(shader);
		shader = NULL;
	}

	currentFilename = (wchar_t*)filename;

	HANDLE hFile = winopen(filename, L'r');

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

	CloseFile(hFile);
}



static void AskForFileThenCheckForErrors()
{
	stopRendering = true;

	PWSTR filename = AskOpenFilename();
	if (!filename)
	{
		MessageBoxA(NULL, "Validate SHA Cancelled", "", MB_ICONINFORMATION);
		stopRendering = false;
		return;
	}

	CheckForErrors(filename, true);
}

static void CheckForErrors(PWSTR filename, bool showSuccess)
{
	stopRendering = true;

	OpenShader(filename);
	LPD3DXBUFFER errors;
	D3DXCreateEffect(d3dDevice, shader, shaderLength, NULL, NULL, D3DXSHADER_USE_LEGACY_D3DX9_31_DLL, NULL, &pEffect, &errors);

	UINT messageType = MB_ICONINFORMATION;
	if (errors)
	{
		messageType = MB_ICONERROR;
		errs = (char*)errors->GetBufferPointer();
		errsize = errors->GetBufferSize();
	}
	else
	{
		if (pEffect)
		{
			errs = (char*)"No errors, yay!";
			errsize = 15;

			pEffect->SetTechnique("T0");
			pEffect->SetTexture(pEffect->GetParameterByName(NULL, "Tex0"), pBaseColour);
			pEffect->SetTexture(pEffect->GetParameterByName(NULL, "Tex1"), pSpecular);
			pEffect->SetTexture(pEffect->GetParameterByName(NULL, "Tex2"), pDirt);
			pEffect->SetTexture(pEffect->GetParameterByName(NULL, "Tex3"), pLighting);
		}
		else
		{
			errs = (char*)"No errors, but the pointer came back NULL";
			errsize = 42;
		}
		
	}

	if (showSuccess || messageType == MB_ICONERROR)
			MessageBoxA(g_hWnd, errs, "Result:", messageType);

	stopRendering = false;
}



static void SwitchToCube()
{
	ChangeMesh(L"cube.x");
}

static void SwitchToSphere()
{
	ChangeMesh(L"sphere.x");
}

static void SwitchToTeapot()
{
	ChangeMesh(L"teapot.x");
}

static void SwitchToSuzanne()
{
	ChangeMesh(L"suzanne.x");
}

static void CreateUIElements(HWND hWnd)
{
	CreateButton(hWnd, L"Validate SHA", 550, 200, 400, 100, AskForFileThenCheckForErrors);
	CreateButton(hWnd, L"Cube", 550, 350, 100, 40, SwitchToCube);
	CreateButton(hWnd, L"Sphere", 650, 350, 100, 40, SwitchToSphere);
	CreateButton(hWnd, L"Teapot", 750, 350, 100, 40, SwitchToTeapot);
	CreateButton(hWnd, L"Suzanne", 850, 350, 100, 40, SwitchToSuzanne);
}

// I implemented this a long time ago, I can't remember where I got it from.
D3DXMATRIX ProjectionMatrix(
	const float near_plane, // Distance to near clipping plane

	const float far_plane,  // Distance to far clipping plane

	const float fov_horiz,  // Horizontal field of view angle, in radians
	const float fov_vert)   // Vertical field of view angle, in radians
{
	float    h, w, Q;

	w = (float)1 / tan(fov_horiz * 0.5);  // 1/tan(x) == cot(x)
	h = (float)1 / tan(fov_vert * 0.5);   // 1/tan(x) == cot(x)
	Q = far_plane / (far_plane - near_plane);

	D3DXMATRIX ret;
	ZeroMemory(&ret, sizeof(ret));

	ret(0, 0) = w;
	ret(1, 1) = h;
	ret(2, 2) = Q;
	ret(3, 2) = -Q * near_plane;
	ret(2, 3) = 1;
	return ret;
}   // End of ProjectionMatrix

float timer = 0.f;

D3DXMATRIX projectionMatrix;
D3DXMATRIX viewMatrix;
D3DXMATRIX worldMatrix;

// I went through and figured out the values for all of these, (based on their colour so there's probably some precision lost with rounding).
// There's a lot, I've only gone through the ones referenced by pro_car_body.
float PLANEX[] = { 0.09019f, 0.23137f, 0.0, 0.27843f };
float PLANEY[] = { 0.08627f, 0.2549f, 0.0f, 0.3098f };
float PLANEZ[] = { 0.0666f, 0.2823f, 0.0f, 0.3647f };
float SOMETHING[] = { 0.0f, 0.5f, 1.0f, 1.0f };
float TIME[] = { 0.0f, 0.0f, 0.0f, 0.0f };

float PS_C0[] = { 0.5f, 0.5f, 0.5f, 0.0f };
float overlighting_limiter[] = { 1.0f, 1.0f, 1.0f, 0.8509f };
float SHADOW[] = { 0.8f, 0.7607f, 0.68627f, 1.0f };

void SetupMatrices()
{
	D3DXVECTOR3 eye(sinf(timer) * CAMERA_DISTANCE, cosf(timer) * CAMERA_DISTANCE, 1.f);
	timer += 0.01f;
	static D3DXVECTOR3 at(0, 0, 0);
	static D3DXVECTOR3 up(0, 0, 1);
	D3DXMatrixLookAtLH(&viewMatrix, &eye, &at, &up);

	// Rotates by 90 degrees so that up is Z instead of Y
	// Used to be needed when I used D3DX functions to create meshes, but I couldn't get UVs that way so I ended up using blender.
	// It's still here so that there's a difference between local and world, so it's easier to tell when it hasn't been accounted for.
	D3DXMatrixRotationX(&worldMatrix, 3.14159f/2);

	projectionMatrix = ProjectionMatrix(0.1f, FAR_CLIP, 1.5708f, 1.5708f);

	projectionMatrix = worldMatrix * viewMatrix * projectionMatrix;

	// The D3DXMATRIX and HLSL matrix are incompatible for some reason, so it has to be transposed.
	D3DXMATRIX transposed;
	D3DXMatrixTranspose(&transposed, &projectionMatrix);
	d3dDevice->SetVertexShaderConstantF(0, (float*)transposed.m, 4);

	D3DXMatrixTranspose(&transposed, &worldMatrix);
	d3dDevice->SetVertexShaderConstantF(4, (float*)transposed.m, 4);

	float CAMERA[] = { eye.x, eye.y, eye.z, 0.0f };
	d3dDevice->SetVertexShaderConstantF(8, CAMERA, 1);
	
	TIME[0] = TIME[1] = TIME[2] = TIME[3] = timer;
	d3dDevice->SetVertexShaderConstantF(14, TIME, 1);

	if (!pEffect)
	{
		d3dDevice->SetTransform(D3DTS_PROJECTION, &projectionMatrix);
		d3dDevice->SetTransform(D3DTS_WORLD, &worldMatrix);
	}
}

void NewUndefinedMat()
{
	mat.Diffuse.r = 0.8f;
	mat.Diffuse.g = 0.8f;
	mat.Diffuse.b = 0.8f;
	mat.Diffuse.a = 1.0f;

	mat.Ambient.r = 1.0f;
	mat.Ambient.g = 1.0f;
	mat.Ambient.b = 1.0f;
	mat.Ambient.a = 1.0f;

	mat.Specular.r = 1.0f;
	mat.Specular.g = 1.0f;
	mat.Specular.b = 1.0f;
	mat.Specular.a = 1.0f;
	mat.Power = 50.0f;

	mat.Emissive.r = 0.7f;
	mat.Emissive.g = 0.0f;
	mat.Emissive.b = 1.0f;
	mat.Emissive.a = 1.0f;
}


void ChangeMesh(const wchar_t* filename)
{
	RELEASE(pMesh);

	LPD3DXBUFFER buffer, materials, effects;
	DWORD numMats;

	if (filename)
		check(D3DXLoadMeshFromXW((LPCWSTR)filename, 0, d3dDevice, &buffer, &materials, &effects, &numMats, &pMesh), "Failed to load mesh: %s");
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
		return FALSE;

	g_hWnd = hWnd;

	if (!InitD3D(hWnd))
		return FALSE;

	LoadTextures();

	ChangeMesh(L"sphere.x");

	CreateUIElements(hWnd);

	NewUndefinedMat();

	d3dDevice->SetRenderState(D3DRS_ZENABLE, TRUE);
	d3dDevice->SetRenderState(D3DRS_ZWRITEENABLE, TRUE);
	d3dDevice->SetRenderState(D3DRS_ANTIALIASEDLINEENABLE, TRUE);
	d3dDevice->SetRenderState(D3DRS_ZFUNC, D3DCMP_LESSEQUAL);
	d3dDevice->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE);

	d3dDevice->SetFVF(D3DFVF_XYZ | D3DFVF_NORMAL | D3DFVF_DIFFUSE | D3DFVF_TEX1);

	d3dDevice->SetVertexShaderConstantF(15, SOMETHING, 1);

	d3dDevice->SetVertexShaderConstantF(17, PLANEX, 1);
	d3dDevice->SetVertexShaderConstantF(18, PLANEY, 1);
	d3dDevice->SetVertexShaderConstantF(19, PLANEZ, 1);

	d3dDevice->SetVertexShaderConstantF(22, SHADOW, 1);

	d3dDevice->SetPixelShaderConstantF(0, PS_C0, 1);
	d3dDevice->SetPixelShaderConstantF(1, overlighting_limiter, 1);
	d3dDevice->SetPixelShaderConstantF(2, SHADOW, 1);

	ShowWindow(hWnd, nCmdShow);
	UpdateWindow(hWnd);

	SetTimer(hWnd, 1, 1, NULL);

	return TRUE;
}

BOOL FileHasUpdated(PWSTR filename, time_t* oldmtime)
{
	struct _stat info;
	BOOL out;

	if (!_wstat(filename, &info))
	{
		out = info.st_mtime != *oldmtime;
		*oldmtime = info.st_mtime;
		return out;
	}

	return false;
}

HBRUSH backgroundColour = CreateSolidBrush(RGB(10, 10, 10));


void Render(RECT* rect)
{
	if (stopRendering) return;

	static RECT titleRect = { 500, 50, 1024, 150 };
	static RECT descRect = { 500, 100, 1024, 200 };
	static RECT disclaimerRect = { 500, 150, 1024, 250 };

	static RECT dxSourceZone = { 0, 0, 500, 500 };
	static D3DRECT clearZone = { 0, 0, 500, 500 };

	PAINTSTRUCT ps;
	HDC hdc = BeginPaint(g_hWnd, &ps);

	HGDIOBJ prevObject = SelectObject(hdc, backgroundColour);
	Rectangle(hdc, rect->left, rect->top, rect->right, rect->bottom);
	SelectObject(hdc, prevObject);

	SetTextColor(hdc, RGB(255, 255, 255));
	SetBkColor(hdc, RGB(10, 10, 10));
	DrawTextA(hdc, "Zack's FlatOut Shader Validator and Viewer", 43, &titleRect, DT_CENTER);
	DrawTextA(hdc, "This app compiles the SHA just like the game,\nexcept it will show you the errors.", 82, &descRect, DT_CENTER);
	DrawTextA(hdc, "It also shows a preview of the shader.", 39, &disclaimerRect, DT_CENTER);

	
	if (currentFilename && FileHasUpdated(currentFilename, &testmtime))
	{
		CheckForErrors(currentFilename, false);
	}
	
	RECT dxRenderZone = { rect->left + 500, rect->right, rect->top, rect->bottom };


	if (d3dDevice && pMesh)
	{
		d3dDevice->Clear(1, &clearZone, D3DCLEAR_TARGET | D3DCLEAR_ZBUFFER, RGB(100, 100, 100), FAR_CLIP, 0);
		SetupMatrices();
		HRESULT hr = d3dDevice->BeginScene();
		if (SUCCEEDED(hr))
		{
			if (pEffect)
			{
				UINT passes;
				check(pEffect->Begin(&passes, 0), "Failed to begin effect: %s");
				for (UINT i = 0; i < passes; i++)
				{
					check(pEffect->BeginPass(i), "Failed to begin pass: %s");
					pMesh->DrawSubset(0);
					pEffect->EndPass();
				}
				pEffect->End();	
			}
			else
			{
				d3dDevice->SetMaterial(&mat);
				pMesh->DrawSubset(0);
			}
			d3dDevice->EndScene();
		}
		else
			PrintD3DError(hr, "Failed to BeginScene: %s");

		d3dDevice->Present(&dxSourceZone, &dxSourceZone, g_hWnd, NULL);
	}

	EndPaint(g_hWnd, &ps);
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
	RECT clientRect;
	switch (message)
	{
	case WM_COMMAND:
	{
		int notif = HIWORD(wParam);
		
		if (notif == BN_CLICKED)
		{
			int dex;
			dex = GetButtonIndex((HWND)lParam);
			if (dex != -1)
				OnClicks[dex]();
		}
		else
		{
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
		RECT rect = { 0, 0, 400, 400 };
		GetClientRect(hWnd, &rect);
		Render(&rect);
	}
	break;

	case WM_TIMER:
		GetClientRect(hWnd, &clientRect);
		Render(&clientRect);
		break;

	case WM_DESTROY:
		free(shader);
		DeInitD3D();
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
