# Zack's High Level Shader Language (HLSL) To FlatOut Shader (SHA)
It's a python script that converts an HLSL script into assembly and creates an SHA file from it for use in FlatOut 1 or 2.
<br>
*(It was originally made for 2 but I checked and the first game uses the exact same format)*

<br>

Right now it only supports writing pixel shaders, vertex shader support is still being worked on

<br>

## Using the Script
<br>
At the start it'll prompt you for an HLSL file to convert. The resulting shader file will be in the same spot with the same name, just with the .sha extension.
<br>
<br>
The script also has the option to run in a loop, so that when it detects the file has changed, it'll automatically recompile. Useful for debugging, and maybe other things too.

<br><br>

## HLSL

### The Pixel Shader
The main thing you need is to define the PixelShader function, like so:
```hlsl
float4 PixelShader()
{
  // All code in here will end up in the pixel shader of the SHA file
}
```
It can be called PixelShader, psMainD3D9, or just psMain

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
<br>

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

<br><br>

### Math

There can only be 1 math expression in a line (except for a few cases), but other than that its exactly how you'd expect, except dividing can only be done by 2.

For example:
```hlsl
myVar = colour + specular;
myVar *= lighting;
myVar -= dirt;
myVar = colour / 2;
```

<br><br>

### Modifiers

Modifiers are addons to instructions, allowing you to do more in a single instruction. You're likely already familiar with saturate(), but there's more math related ones
<br>
- d2 : divide the result by 2
- x2 : multiply the result by 2
- x4 : multiply the result by 4
<br>
Each of these math modifiers can be used in either function form, exactly like saturate, or in it's math expression form. This is the only case where 2 math expressions can be on one line.

```hlsl
myVar = d2(specular * FRESNEL);
// or
myVar = (specular * FRESNEL) / 2;

myVar = x2(specular * FRESNEL);
// or
myVar = specular * FRESNEL * 2;

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

<br><br>

### Assembly

The ```asm``` keyword can be used to insert assembly if you absolutely have to
```hlsl
float4 myVar = colour;
asm
{
  mov r0, t0
}
```

<br><br>

Lastly, there are some special constants that the game uses, those can be accessed with keywords
- SHADOW : The shadow mask of the track
- AMBIENT : Ambient lighting
- FRESNEL : Fresnel term
- BLEND : The car body shaders use a texture to blend between clean and dirt

So in summary I can write a car body shader like this:
```hlsl
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

Bonus tip: The return value and all of the parameters are always float4 so the type is optional.
```hlsl
PixelShader(colour, specular, dirt, lighting)
{
    float4 brightness = float4(0.0f, 0.0f, 0.0f, 0.75f);
    float4 c = specular * FRESNEL;
    //...
}
```

<br><br>

# Troubleshooting
There are some very specific limitations with the assembly [which are documented here](https://learn.microsoft.com/en-us/windows/win32/direct3dhlsl/dx9-graphics-reference-asm-ps-1-x), so even though the HLSL may compile fine, that doesn't mean FlatOut 2 will be able to compile it.

<br><br>

Here's what I know so far:

<br>

The r registers (the variables in HLSL) cannot be read from twice in a row, this is a software limitation imposed by the game, I don't know why outside of security maybe.
```hlsl
float4 var1 = specular * FRESNEL;
float4 var2 = var1;
var2 = var1; // The game can't compile this, you need to write to var1 before reading again
```

<br>

Use ```ZacksShaderValidator.exe``` to check if the shader will run in-game.

Clicking 'Validate SHA' will prompt you for an SHA file to validate, then show the errors in a message box.
