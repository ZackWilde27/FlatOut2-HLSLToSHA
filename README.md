### I learned that you can put HLSL in the shader file
I made a page explaining it [here](https://github.com/ZackWilde27/FlatOut2-HLSLToSHA/wiki/Putting-HLSL-in-the-shader-file)

I've tried to make my version the easier way to write shaders, but if you want standard HLSL, I just thought I'd mention it right off the bat.

<br>

# Zack's High Level Shader Language (HLSL) To FlatOut Shader (SHA)
It's a python script that converts an HLSL script into assembly and creates an SHA file from it for use in FlatOut 1 or 2.
<br>
*(It was originally made for 2 but I checked and the first game uses the exact same format)*

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
# For loop, "" means to ask, otherwise it's bool(x)
loop = ""
```
Leaving them as "" means that it will ask you when the script runs, so you can set it up to ask you every question or none at all.

It's actually a python script so theoretically any variable from the script can be changed in there

<br><br>

# HLSL

## Defining the Pixel Shader
The pixel shader function can be called PixelShader, psMainD3D9, or just psMain

It returns the final colour of the pixel
```hlsl
float4 PixelShader()
{
  // All code in here will end up in the pixel shader of the SHA file
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
*Note, the (N * L) is dot product, not multiply, so it basically means directional lighting*

So my re-implementation would look something like this:

```hlsl
float4 PixelShader(float4 colour, float4 specular, float4 dirt, float4 lighting)
{
  //...
}
```

<br>

## Defining the Vertex Shader
The vertex shader can be called VertexShader, vsMainD3D9, vsMain, or just main

It returns the position of the vertex in view space
```hlsl
float4 VertexShader()
{
  // All code in here will end up in the vertex shader of the SHA file
}
```

These inputs require type and semantics, as it's up to you which inputs are given to the shader.

The syntax for the inputs is ```type``` ```name``` : ```semantic```

The semantics are:
- POSITION, VPOS, or SV_Position (float3)
- NORMAL (float3)
- COLOR or SV_Target (float4)
- TEXCOORD (float2) (this one can have an index at the end like TEXCOORD0 or TEXCOORD1)

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
<br>
<br>


# Writing the Pixel Shader

### Variables

FlatOut 2 uses HLSL assembly 1.1 - 1.3, and those ones are extremely basic so the HLSL has some quirks.

You can only have 2 variables, because there's 2 registers to hold values
```hlsl
float4 var1 = colour + specular;
float4 var2 = lerp(var1, dirt, specular.a);
float4 var3 = dirt; // This will be treated as var2, overwriting the previous lerp
```

Though, you can have up to 5 constants, which can hold misc. data for use in the shader (It's actually 8, but the game reserves the first 3)
```hlsl
float4 const1 = float4(0.0f, 0.0f, 1.0f, 1.0f);
float4 const2 = float4(1.0f, 1.0f, 1.0f, 1.0f);
//...
```

<br>

### Intrinsic Functions

The supported intrinsic functions are as follows:
- dot()
- lerp()
- saturate()
- mad()

Saturate is the only function that can have math or other functions inside it, the rest have to be structured ```xyz = function()``` or ```return function()```

For example:
```hlsl
float4 myVar = dot(colour, specular);
myVar = saturate(mad(dirt, specular, lighting));
myVar = lerp(colour, dirt, lighting.a);
return dot(specular, dirt);
```

<br>

### Math

There can only be 1 math expression in a line (except for a few cases), but other than that it's exactly how you'd expect, except dividing can only be done by 2.

For example:
```hlsl
myVar = colour + specular;
myVar *= lighting;
myVar -= dirt;
myVar = colour / 2;

myVar = -colour;
// You can also do 1-x
myVar = 1-colour * 1-specular;
```

<br>

### Modifiers

Modifiers are addons to instructions, allowing you to do more in a single instruction. You're likely already familiar with saturate(), but there's more math related ones
<br>
- d2 : divide the result by 2
- x2 : multiply the result by 2
- x4 : multiply the result by 4
<br>
Each of these math modifiers can be used in either function form, exactly like saturate, or in its math expression form. This is the only case where 2 math expressions can be on one line.

```hlsl
myVar = d2(specular * FRESNEL);
// or
myVar = (specular * FRESNEL) / 2;

myVar = x2(specular * FRESNEL);
// or
myVar = specular * FRESNEL * 2;

// I also gave them more natural names like saturate(), but you can still use the other ones
// half() == d2()
// double() == x2()
// quad() == x4()
myVar = half(specular * fresnel)

// Also, they can be stacked, and in any order
myVar = x2(d2(saturate(x4(specular * FRESNEL))));
```

<br>

### If statements

An if statement is technically possible, but it's extremely limited.
```hlsl
float4 var1 = colour;
float4 var2 = ? AMBIENT : SHADOW;

// The comparison being done here is (r0.a > 0.5), r0 is your first variable, so in this case it'd be var1
// So it's essentially:
//var2 = (var1.a > 0.5) ? AMBIENT : SHADOW;
```

<br>

### Functions
In the pixel shader, there's no way to call functions, so these are defines that can have multiple lines, as-in they will copy+paste the code inside.
All functions have to return a value, because it has to be structured just like the instrinsic functions
```hlsl
float4 psMainD3D9(float4 colour, float4 specular)
{
  // The parameter types are optional
  float4 myDot(a, b)
  {
    a = colour * b;
    return dot(a, b);
  }

  // It's supposed to be possible to write to a texture register in the pixel shader but in my experience the game doesn't compile it
  float4 myVar = colour;

  return myDot(myVar, specular);
}
```


<br>

### Splitting Vectors

In ps.1.1, splitting can only be done if it's the alpha channel
```hlsl
myVar = SHADOW.a;
myVar = AMBIENT.aaaa * myVar.a;

myVar = SHADOW.x; // The game can't compile this
```

Using z/b is possible, but only when the destination is the alpha channel
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

Lastly, there are some special constants that the game uses, those can be accessed with keywords
- SHADOW : The shadow mask of the track
- AMBIENT : Ambient lighting
- FRESNEL : Fresnel term
- BLEND : The car body shaders use a texture to blend between clean and dirt
- EXTRA : From what I can tell it's either unused or a duplicate of something else

<br><br>

<br><br>

# Writing the Vertex Shader

Math, function, and assembly syntax is exactly the same as the pixel shader, so I won't go over those

### Returning
Normally the vertex shader is a void function, but since you have to write to the position register at some point, I made that the return value.

```hlsl
float4 VertexShader(float3 pos : POSITION)
{
  return pos.xyzz;
}
```

<br>

### Variables

You can have up to 12 variables, because there's 12 registers to hold values
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
//...
```

<br>

### Intrinsic Functions

The supported intrinsic functions are as follows:
- abs()
- distance() / dst()
- dot()
- exp2() (exp2_full() to use the accurate but expensive version)
- frac()
- length()
- log2() (log2_full() to use the accurate but expensive version)
- mad()
- max()
- min()
- normalize()
- reflect()
- rcp()
- rsqrt()

These have to be structured ```xyz = function()``` or ```return function()```

For example:
```hlsl
float4 myVar = reflect(nrm, pos);
myVar = mad(uv1.x, uv2.y, diff.z);
myVar = max(myVar, nrm);
return normalize(nrm);
```

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
float4 var2 = LocalToWorld(pos);
float4 var1 = WorldToView(pos);
```

<br>

### If statements
If statements are technically possible, but they are extemely limited, and in a completely different way.
```hlsl
float4 var1 = pos;
float4 var2 = var1.x > pos.y ?;
// It can be >, <, >=, or <=

// The values being returned here are 1.0 and 0.0,
// So it's basically
// var2 = (var1.x > pos.y) ? 1.0 : 0.0;
```

<br>

### Splitting Vectors

In vs.1.1, splitting/swizzling is a lot less restrictive.
```hlsl
myVar.zyx = nrm.xyz;
myVar = pos.yzx * myVar.yxz;
```

<br><br>

Lastly, there are some special constants that the vertex shader uses, as I figure more of them out I'll add them here
- CAMERA : The position of the camera in world space

<br><br>

So in summary I can write a car body shader like this:
```hlsl
float4 VertexShader(float3 pos : POSITION, float3 nrm : NORMAL, float4 diff : COLOR, float2 uvs : TEXCOORD)
{
  colour.uv = uvs.xy;
  dirt.uv = uvs.xy;

  float3 worldNormal = LocalToWorld(nrm);

  // The lighting cubemap can just be given the world normal
  lighting.xyz = worldNormal;

  // Calculate the reflection vector for the specular cubemap
  float4 incident = pos - CAMERA;
  incident = normalize(incident);
  specular.xyz = reflect(incident, worldNormal);

  // The blend factor for the car body comes from the COLOR input
  BLEND = diff;
  // TODO: Add fresnel calculations
  FRESNEL = mySuperAwesomeFresnelFunction();

  // I'm still figuring out the input ambient constants and how those should work, for now I'd use a function with assembly
  float3 GetAmbient(float3 normal)
  {
    asm
    {
      dp4   r4.x, %1, c17
      dp4   r4.y, %1, c18
      dp4   r4.z, %1, c19
      mov   %0, r4
    }
  }
  AMBIENT = GetAmbient(worldNormal);

  return WorldToView(pos);
}


float4 PixelShader(float4 colour, float4 specular, float4 dirt, float4 lighting)
{
    float4 brightness = float4(0.0f, 0.0f, 0.0f, 0.75f); // a = ambient multiplier

    float4 c = specular * FRESNEL;
    float4 l = lerp(colour, dirt, BLEND);
    c = saturate(c + l);
    l = lighting * SHADOW;
    l = saturate(mad(AMBIENT, brightness.a, l));
    return c * l;
}
```

<br><br>

Bonus tip: The return value is always float4 so it's optional.
```hlsl
VertexShader(float3 pos : POSITION)
{
    //...
}

// For the pixel shader, the parameters don't need the type either since it's always float4
PixelShader(colour, specular, dirt, lighting)
{

}
```


<br><br>

# Troubleshooting
There are some very specific limitations with the assembly [which are documented here](https://learn.microsoft.com/en-us/windows/win32/direct3dhlsl/dx9-graphics-reference-asm-ps-1-x), so even though the HLSL may compile fine, that doesn't mean FlatOut 2 will be able to compile it.

Use ```ZacksShaderValidator.exe``` to check if the shader will run in-game.

Clicking 'Validate SHA' will prompt you for an SHA file to validate, then show the errors in a message box.
