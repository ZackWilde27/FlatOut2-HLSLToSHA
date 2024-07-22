# Zack's HLSL To FlatOut 2 Shader
It's a python script that takes an HLSL script and creates an SHA file from it for use in FlatOut 1 or 2.
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

The inputs of the PixelShader function corrospond to texture samples, so to output the first texture:
```hlsl
float4 PixelShader(float4 tex0)
{
  return tex0;
}
```

The type of texture that it corrosponds to is determined by the original shader that you are overriding.

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
float4 var3 = dirt; // This will cause issues or fail to compile
```

Though, you can have up to 30 constants, which can hold misc. data for use in the shader
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

Saturate is the only function that can have math or other functions inside it, the rest have to be structured 'xyz = function()'

For example:
```hlsl
float4 myVar = dot(colour, specular);
myVar = saturate(mad(dirt, specular, lighting));
myVar = lerp(colour, dirt, lighting.a);
```

<br><br>

### Math

There can only be 1 math expression in a line, but other than that its exactly how you'd expect, except there's no divide.

For example:
```hlsl
myVar = colour + specular;
myVar *= lighting;
myVar -= dirt;
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
    float4 c = specular * FRESNEL;
    c = saturate(c + colour);
    float4 l = lighting * SHADOW;
    l = saturate(l + AMBIENT);
    return c * l;
}
```

# Troubleshooting
There are some very specific limitations with the assembly [which are documented here](https://learn.microsoft.com/en-us/windows/win32/direct3dhlsl/dx9-graphics-reference-asm-ps-1-x), so even though the HLSL may compile fine, that doesn't mean FlatOut 2 will be able to compile it.

<br>

If it fails the only error message you will get says "Failed to create effect" with no explanation, but the error message exists in the game's memory. Using cheat engine if you search for the string "X error" you will find all of the compiler errors.
