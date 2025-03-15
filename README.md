### The future of the compiler
I found out that the game supports up to shader model 3, so now my recommendation is to write it [the conventional way](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/wiki/Putting-HLSL-in-the-shader-file). I'm considering a few options, like upgrading to 3.0 assembly, or making a new source-to-source compiler.

I want to keep the current version around, since shader model 1 is not officially supported by Microsoft anymore, and it might be possible to use it for other games.

<br>

# Zack's High Level Shader Language (HLSL) To FlatOut Shader (SHA)
It's a python script that converts an HLSL script to assembly and creates an SHA file from it for use in FlatOut 1 or 2.
<br>
*(It was originally made for 2 but I checked and the first game uses the exact same format)*

Table of Contents
- [Using the Script](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/blob/main/README.md#using-the-script)

- [Defining the PixelShader](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/blob/main/README.md#defining-the-pixel-shader)

- [Defining the VertexShader](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/blob/main/README.md#defining-the-vertex-shader)

- [Defining the Technique](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA?tab=readme-ov-file#defining-the-technique)

- [Writing the PixelShader](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/blob/main/README.md#writing-the-pixel-shader)
	- [Variables](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#variables)
  	- [Keywords](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#keywords)
	- [Intrinsic Functions](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#intrinsic-functions)
	- [Math](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#math)
	- [Modifiers](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#modifiers)
	- [Inline Ifs](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#inline-ifs)
	- [For loops](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#for-loops)
	- [Preprocessor](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#preprocessor)
	- [Functions](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#functions)
	- [Meanwhile](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#meanwhile)
	- [Swizzling Vectors](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#swizzling-vectors)
	- [Assembly](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#assembly)
	- [Strings](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#strings)

- [Writing the VertexShader](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/blob/main/README.md#writing-the-vertex-shader)
	- [Variables](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#variables-1)
	- [Arrays](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#arrays)
  	- [Keywords](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#keywords-1)
	- [Intrinsic Functions](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#intrinsic-functions-1)
	- [Textures](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#textures)
	- [Colour Registers](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#colour-registers)
	- [Transforming](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#transforming)
	- [Inline Ifs](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#inline-ifs-1)
	- [Swizzling Vectors](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/tree/main?tab=readme-ov-file#swizzling-vectors-1)

- [Troubleshooting](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/blob/main/README.md#troubleshooting)

- [Using the Decompiler](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/blob/main/README.md#using-the-decompiler)

<br>

## Using the Script


At the start it'll prompt you for an HLSL file to convert. The resulting shader file will be in the same spot with the same name, just with the .sha extension.

<br>

The script also has the option to run in a loop, so that when it detects the file has changed, it'll automatically recompile. Useful for debugging, and maybe other things too.

<br>

The script will create a ```settings.txt``` file when launching for the first time
```
filename = ""
author = ""
loop = "" # empty string means to ask, otherwise it's bool(loop)
```
Leaving them as "" means that it will ask you when the script runs, so you can set it up to ask you every question or none at all.

It's actually a python script so theoretically any variable from the script can be changed in there.

<br><br>

## Defining the Pixel Shader
The pixel shader function can be called PixelShader, psMainD3D9, or just psMain

It returns the final colour of the pixel
```hlsl
float4 PixelShader()
{
    // Code in here will run for every pixel drawn
}
```

The inputs of the PixelShader function corrospond to texture samples, so to output the first texture:
```hlsl
float4 PixelShader(float4 tex0)
{
    return tex0;
}
```

The type of texture is determined by the original shader that you are overriding.

The original car body shader's textures are arranged like so in the original file:
```
tex		t0	; Base color
tex		t1	; Reflection + specular alpha
tex		t2	; Dirt
tex		t3	; N * L
```
*Note: the (N * L) is dot product, not multiply, so it basically means directional lighting*

So my re-implementation would look something like this:

```hlsl
float4 PixelShader(float4 colour, float4 specular, float4 dirt, float4 lighting)
{
    //...
}
```

If it uses an instruction other than ```tex``` to sample the texture, it can be specified instead of the type:
```hlsl
float4 PixelShader(texcoord colour, texkill specular) {}

// texcoord means that instead of sampling the texture, the parameter will contain the UVs
// texkill means that if any of its UV coordinates are less than 0, don't render this pixel
```


<br>


## Defining the Vertex Shader
The vertex shader can be called VertexShader, vsMainD3D9, vsMain, or just main

It returns the position of the vertex in screen space
```hlsl
float4 VertexShader()
{
    // Code in here will run for each vertex in the mesh
}
```

These inputs require semantics, as it's up to you which ones are given to the shader

For example:
```hlsl
float4 VertexShader(float3 pos : POSITION, float3 nrm : NORMAL, float2 uv : TEXCOORD)
{

}

// or

float4 VertexShader(float3 pos : POSITION, float2 uv1 : TEXCOORD0, float2 uv2 : TEXCOORD1)
{

}
```
[Full list of semantics](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/wiki/Vertex-Shader-Semantics)


<br>


## Defining the Technique
You have the choice to add a Technique/Pass to your shader if the original shader needs more setup than just the shaders and textures

For example, setting up the technique for the pro_sunflare shader would look like this:
```hlsl
float4 VertexShader() { ... }

float4 PixelShader() { ... }

Technique T0
{
    Pass P0
    {
        MinFilter[1] = Point;
        MagFilter[1] = Point;
    }
}
```


<br>
<br>


# Writing the Pixel Shader

### Variables

FlatOut 2 uses Shader Model 1, which is extremely basic so the HLSL has some quirks.

There's only 2 registers that can be both read and written to, so you are limited to 2 variables at one time.
```hlsl
float4 var1 = colour + specular;
float4 var2 = lerp(var1, dirt, specular.a);
float4 var3 = dirt; // This will be treated as var2, overwriting the previous lerp
```

The compiler will recognize when variables are no longer needed to free-up registers, allowing for what looks like more than 2 variables
```hlsl
float4 PixelShader()
{
    float4 var1 = colour + specular;
    float4 var2 = var1 + dirt;

    // var1 is not referenced beyond this point, so another variable can take its place
    float4 var3 = var2 + lighting.a;
    return var3;
}
```

Though, you can have up to 5 constants, which can hold misc. data for use in the shader (It's actually 8, but the game reserves the first 3)
```hlsl
// Everything is clamped between -1 and 1 in the pixel shader.
const float4 const1 = float4(0.0f, 0.0f, 1.0f, 1.0f);
const float4 const2 = float4(1.0f, 1.0f, 1.0f, 1.0f);
// the const keyword is optional
float4 const3 = float4(1.0f, 1.0f, 0.0f, 0.0f);
// Though a single float will confuse it, so make sure to put const
const float const4 = 1.0f;
//...
```


<br>

### Keywords
Reserved constants and other registers can be accessed with keywords
- SHADOW : The shadow mask of the track
- AMBIENT : Ambient lighting
- FRESNEL : Fresnel term
- BLEND : The car body shaders use vertex colours to blend between clean and dirt
- EXTRA : From what I can tell it's either unused or a duplicate of something else

<br>


### Intrinsic Functions

The supported intrinsic functions are as follows:
- dot()
- lerp()
- saturate()
- mad()

For example:
```hlsl
float4 myVar = dot(colour, specular);
myVar = saturate(mad(dirt, specular, lighting.a));
myVar = lerp(colour, dirt, dot(colour, specular));
return dot(specular, dirt);
```


<br>


### Math

The syntax is just like HLSL/C, but there are some things I should mention

In the pixel shader, dividing can only be done by 2
```hlsl
myVar = colour + specular;
myVar *= lighting.a;
myVar -= dirt;
myVar = colour / 2;

myVar = -colour;
// The pixel shader can do 1-x for free
myVar = 1-colour * 1-specular;
```

When putting multiple math statements in a line, it does not follow the order of operations, it will perform each operation in the order you wrote it
```hlsl
float4 myFloat = colour + specular * lighting.a + AMBIENT;
// from the compiler's perspective looks like this:
float4 myFloat = ((colour + specular) * lighting.a) + AMBIENT;
```

Also the destination is used to store the immediate results, so it can't be part of the equation unless it's in the first operation
```hlsl
// myFloat will get overwritten with (colour + specular) before the multiply, losing the value that was stored in there.
myFloat = colour + specular * myFloat;

// This one shouldn't cause problems
myFloat = specular * myFloat + colour;
```


<br>

### Modifiers

Modifiers are addons to instructions, allowing you to do more in a single instruction. You're likely already familiar with saturate(), but there's more math related ones
<br>
- d2 : divide the result by 2
- x2 : multiply the result by 2
- x4 : multiply the result by 4
<br>
Each of these math modifiers can be used in either function form, exactly like saturate, or in its math expression form.

```hlsl
myVar = d2(specular * FRESNEL);
// or
myVar = specular * FRESNEL / 2;

myVar = x2(specular * FRESNEL);
// or
myVar = specular * FRESNEL * 2;

// I also gave them more natural names like saturate(), but you can still use the other ones
// half() == d2()
// double() == x2()
// quad() == x4()
myVar = half(specular * FRESNEL)

// Also, they can be stacked, and in any order
myVar = x2(d2(saturate(x4(specular * FRESNEL))));
```

<br>

### Inline Ifs

If statements are technically possible, but only inline ones, and they are very limited
```hlsl
float4 var1 = colour;
float4 var2 = ? AMBIENT : SHADOW;

// The comparison being done here is (r0.a > 0.5), r0 is your first variable, so in this case it'd be var1
// So it's essentially:
//var2 = (var1.a > 0.5) ? AMBIENT : SHADOW;
```

Now that the compiler uses ps_1_3, you can compare anything to 0 with the format ```x operator 0 ? y : z```

Where ```operator``` can be >= or <
```hlsl
var2 = (lighting.a >= 0) ? colour : specular;
```

<br>

### For loops

In this shader model there is no branching whatsoever, so these for loops have a few limitations:

- The number of iterations has to be pre-determined, since the compiler simply duplicates the code however many times
 
- There's no way to end it early, so you can't ```break```, ```continue```, or ```return```.
```hlsl
for (int i = 0; i < 5; i += 1)
{
    // This code will be duplicated 5 times
    var1 *= 0.5f;
}
```

If the index is referenced, the compiler will insert the code to keep track of it.
```hlsl
for (float i = 1.0f; i > 0.0f; i -= 0.25f)
{
    var1 += i;
}
```

Since Python is the one doing the looping, I added the option to write it in a pythonic way.
```hlsl
// Just like python, it can accept 1-3 inputs indicating the start, end, and step
for i in range(5)
{
    for j in range(5, 50)
    {
        var1 *= 0.5f;
    }
}
```

For loops can be done in the pixel shader but they are a lot more useful in the vertex shader with arrays.

<br>

### Preprocessor
The compiler supports these preprocessor directives:
- #define
- #include
- #ifdef/#ifndef

If you've written C code, you know how these work, but for people who haven't or to clarify:

Define can create a substitution for some other text that gets replaced before the script is compiled, so it could be a stand-in for a type, function, anything really
```hlsl
#define Tint(base, tintval) base * tintval

#define function float4
#define let float4
#define std::cout return
#define << 

function PixelShader(colour, specular) {
    let c = Tint(specular, colour);
    std::cout << c;
}
```

Ifdef/ifndef can be used to either selectively include code, or switch between 2 blocks of code
```hlsl
#define MYDEFINITION

float4 PixelShader(colour, specular)
{
    // This code will only be included if MYDEFINITION is not defined
    #ifndef MYDEFINITION
        float4 thisVariable = colour;
    #endif


    // This one will switch between two blocks of code
    #ifdef MYDEFINITION
        return colour + specular;
    #else
        return thisVariable * specular;
    #endif
}
```

Include is used to paste the contents of another file in a particular location, so you can have commonly-used code in a separate file
```hlsl
// In my 'utils.hlsl' file:
#define Tint(a, b) a * b
```
```hlsl
// Then in the actual file:
#include "utils.hlsl"

float4 PixelShader(colour, specular)
{
    return Tint(colour, specular);
}

```


<br>

### Functions
In this shader model, there's no way to call functions, so these are macros that can have multiple lines, meaning they will copy+paste the code inside.
```hlsl
float4 psMainD3D9(float4 colour, float4 specular, float4 blend)
{
    float4 scratchValue; // reserves r0 for the if statement  

    // Implements (a > b) ? ifA : ifB;
    float4 GreaterThan(a, b, ifA, ifB)
    {
        scratchValue.a = a - b + 0.5f;
        return ? ifA : ifB;
    }

    return GreaterThan(blend, 0.25f, colour, specular);
}
```

<br>

### Meanwhile
The ```meanwhile``` keyword can be used to perform two instructions at the same time

One of them needs to write to .rgb, and the other needs to write to .a
```hlsl
var1.rgb = colour.a;
meanwhile var2.a = colour.a * 2;
```


<br>

### Swizzling Vectors

In the pixel shader, swizzling can only be done if it's ```.xyzw/rgba```, ```.xyz/rgb```, or ```.w/a```
```hlsl
myVar = SHADOW.a;
myVar = AMBIENT.rgb * myVar; // Which is the same as myVar.rgba

myVar = SHADOW.x; // The game can't compile this
```

Using z/b is possible, but only when the destination is w/a
```hlsl
myVar.a = SHADOW.z;
```

<br>

### Assembly

The ```asm``` keyword can be used to insert assembly if you absolutely have to
```hlsl
float4 myVar = colour;
asm
{
    mov r0, t0
    // When inserting assembly in a function, you can access the return value with %0, and the parameters with %1, %2, and so on
    dp3 %0, %1, %2
}
```

<br>

### Strings

Strings can be used to refer to a specific assembly keyword inside an HLSL statement.
For example, if you need to access the c1 register you can simply put it in a string
```hlsl
float4 var1 = "c1";
var1 = "c2" + "c1";
// or even
"r0.a" = dot("c2", "c1");

// This can be combined with macros to create keywords that are specific to your shader
#define AMBIENT "v0"
#define SHADOW "c2"

// The 'string' type is another way to create string macros
string AMBIENT = "v0";
const string SHADOW = "c2";
```

<br><br>

# Writing the Vertex Shader

Math, macro, function, for loops, assembly, and string syntax is exactly the same as the pixel shader, so I won't go over those

### Variables

You can have up to 12 variables, as there's now 12 registers to hold values
```hlsl
float4 var1 = pos + nrm;
float4 var2 = dot(nrm, diff);
float4 var3 = nrm;
float4 var4 = specular;
//...
```

Also, you can have up to 64 constants, which can hold misc. data for use in the shader (It's actually 96, but the game can reserve anywhere from 8 to 32 depending on the shader)
```hlsl
float4 const1 = float4(0.0f, 0.0f, 1.0f, 1.0f);
float4 const2 = float4(1.0f, 1.0f, 1.0f, 1.0f);

// In the vertex shader, you can have integer and boolean constants as well
int4 const3 = int4(1, 2, 3, 4); // ints can be used to index into arrays
bool2 const4 = bool2(true, false); // I don't know what bools are used for
```
In the vertex shader, the compiler will [automatically pack constants together](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/wiki/Vertex-Shader-Constant-Packing) to be more efficient

<br>

### Keywords
- CAMERA : The position of the camera in world space
- PLANEX : The ambient x-plane's normal, in world space
- PLANEY : The ambient y-plane's normal, in world space
- PLANEZ : The ambient z-plane's normal, in world space

<br>


### Arrays
Arrays can be defined with either ```{}``` or ```[]```
```hlsl
float3 list1[1] = [ float3(1.0f, 1.0f, 1.0f) ];

float2 myList[] = {
    float2(1.0f, 0.0f),
    float2(0.0f, 1.0f),
    float2(1.0f, 0.0f)
};
```

They can have items of varying type but they won't be packed together
```hlsl
float4 myList[] =
{
    float2(1.0f, 0.0f),
    float3(0.5f, 0.25f, 0.125f),
    0.75f
};
```

Then the array can be indexed as usual
```hlsl
// floats will be rounded to the nearest integer to get the index
var2 = myList[var1.x * 2.0f] + var1.y;
```

Also, pythonic fors can be used to loop through each item
```hlsl
for i in myList
{
    myVar += i;
}
```

<br>

### Intrinsic Functions

The supported intrinsic functions are as follows:
- abs()
- clamp()*
- degrees()*
- distance()*
- dst()
- dot()
- exp2() (exp2_full() to use the accurate but expensive version)
- floor()*
- frac()
- length()*
- lerp()*
- lit()
- log2() (log2_full() to use the accurate but expensive version)
- mad()
- max()
- min()
- normalize()*
- radians()
- reflect()*
- rcp()
- rsqrt()
- sqrt()*
- step()

*These functions use workarounds that are multiple instructions long, so they aren't as efficient as the other ones

For example:
```hlsl
float4 myVar = reflect(nrm, pos);
myVar = mad(uv1.x, uv2.y, diff.z);
myVar = max(min(myVar, 1.0f), 0.0f);
return normalize(nrm);
```

I also added some new functions in the same vein as rsqrt()
- rlength()
- rdistance()

<br>

### Textures
The vertex shader needs to give each texture its UV coordinates. Its name is the same as defined in the pixel shader, and to load the coordinates use ```tex.uv = ```

For example:
```hlsl
float4 VertexShader(float3 pos : POSITION, float3 nrm : NORMAL, float2 uvs : TEXCOORD)
{
    colour.uv = uvs.xy;

    // Cubemaps use a direction as the coordinates instead of the given UVs
    // For a specular map, you'll want to use the reflection vector
    specular.xyz = nrm;
}

float4 PixelShader(float4 colour, float4 specular)
{
    //...
}
```

<br>

### Colour Registers
FRESNEL, BLEND, AMBIENT and EXTRA can be given values in the vertex shader which will be interpolated to get the value for the pixel shader.
```hlsl
// In a custom shader, this means you have 2 scalar values and 2 colour values to pass to the pixel shader
FRESNEL = uvs.x;
BLEND = uvs.y;

AMBIENT = nrm.xyz;
EXTRA = nrm.xyz;
```

<br>

### Transforming
The game supplies 2 matrices for you to transform with, and to make the whole thing simpler I made them functions:

```hlsl
float4 var1 = LocalToWorld(pos);
float4 var2 = RotateToWorld(pos); // Only does the rotation portion of LocalToWorld()

float4 var3 = LocalToScreen(pos);
```
[I made a page to explain these](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/wiki/Local-vs-World-vs-View-vs-Screen-Space)

<br>

### Inline Ifs
If statements are possible, but extremely limited, and in a completely different way.
```hlsl
float4 var1 = pos;
float4 var2 = var1.x > pos.y ?;
// It can be >, <, >=, or <=

// The values being returned here are 1.0 and 0.0,
// So it's basically
// var2 = (var1.x > pos.y) ? 1.0 : 0.0;
```

<br>

### Swizzling Vectors

In the vertex shader, swizzling is a lot less restrictive.
```hlsl
myVar.zyx = nrm.xyz;
myVar = pos.yzx * myVar.yxz;
```


<br><br>

# Summary
So in summary I can write a car body shader like this:
```hlsl
float4 VertexShader(float3 pos : POSITION, float3 nrm : NORMAL, float4 diff : COLOR, float2 uvs : TEXCOORD)
{
    colour.uv = uvs.xy;
    dirt.uv = uvs.xy;

    float3 worldNormal = RotateToWorld(nrm);

    // The lighting cubemap can just be given the world normal
    lighting.xyz = worldNormal;

    // Calculate the reflection vector for the specular cubemap
    float3 worldPos = LocalToWorld(pos);
    float4 incident = normalize(worldPos - CAMERA);
    specular.xyz = reflect(incident, worldNormal);

    // The blend factor for the car body comes from the COLOR input
    BLEND = diff;

    // Fresnel
    float4 f;
    f.x = abs(dot(incident, worldNormal));
    f.x = 1.0f - f.x;
    f.y = f.x * f.x * f.x;
    FRESNEL = mad(f.y, 0.5f, 0.5f);

    float3 inAmbient;
    inAmbient.x = sqrt(dot(worldNormal, PLANEX));
    inAmbient.y = sqrt(dot(worldNormal, PLANEY));
    inAmbient.z = sqrt(dot(worldNormal, PLANEZ));

    AMBIENT = inAmbient;

    return LocalToScreen(pos);
}


float4 PixelShader(float4 colour, float4 specular, float4 dirt, float4 lighting)
{
    float4 c = specular * FRESNEL;
    c = saturate(c + lerp(colour, dirt, BLEND));
    float4 l = lighting.a * SHADOW;
    l = saturate(mad(AMBIENT, 0.6f, l));
    return c * l;
}
```

<br><br>

Bonus tip: The return value and parameter types can all be assumed so they are optional
```hlsl
VertexShader(pos : POSITION)
{
}

PixelShader(colour, specular, dirt, lighting)
{
}
```


<br><br>

# Troubleshooting
There are some very specific limitations with the assembly [which are documented here](https://learn.microsoft.com/en-us/windows/win32/direct3dhlsl/dx9-graphics-reference-asm-ps-1-x), so even though the HLSL may compile fine, that doesn't mean FlatOut 2 will be able to compile it.

Use ```ZacksShaderValidator.exe``` to check if the shader will run in-game.

Clicking 'Validate SHA' will prompt you for an SHA file to validate, then show the errors in a message box.

<br><br>

# Using the Decompiler
It's a python script that turns an SHA file back into HLSL meant for my compiler.

It's meant to make templates from the original shaders automatically, but it can also be used to verify that the compiler wrote what you told it, just in case.

At the start it'll prompt you for an SHA file to decompile, the resulting hlsl file will be in the same place with _decompiled added to the name.

I'm still going to be focusing on the compiler until it's done, but I got the decompiler working well enough that I decided to release it
