// pro_skin template
// Translation of the original shader

// Makes the shader accurate
#python stopOnReturn = False

#define ONE "c15.z"

// 32 - Skinning data (v2) multiplier
#define skinDataMultiplier "c32"

// 33..36 - Composite View-Projection Matrix
#define viewProj "c33"

float4 VertexShader(float3 pos : POSITION, float3 nrm : NORMAL, float4 boneIndexAndWeight2 : COLOR, float2 uv : TEXCOORD)
{
    float4 worldPos;
    float4 r1;
    float4 r2;
    float4 boneParams;

    // bone index & weight (from D3DCOLOR)
    boneParams = boneIndexAndWeight2 * skinDataMultiplier;

    asm {
        mov		a0.x, r3.b				; 1st bone matrix index
		m4x4	r1, v0, c[a0.x + 37]	; transform by 1st bone matrix
		mov		a0.x, r3.r				; 2nd bone matrix index
		m4x4	r2, v0, c[a0.x + 37]	; transform by 2nd bone matrix
    }

    // final vertex position = weighted position of 2 bones (in world space)
    // 1st bone
    worldPos = r1 * boneParams.g;
    // + 2nd bone
    worldPos = mad(r2, boneParams.a, worldPos);

    // final world => projection
    return mul(worldPos, viewProj);


    //-- vertex normal (weighted from 2 bones, normalized)
    asm {
        mov		a0.x, r3.b
		m3x3	r1, v1, c[a0.x + 37]	; transform normal by 1st bone matrix
		mov		a0.x, r3.r
		m3x3	r2, v1, c[a0.x + 37]	; transform normal by 2nd bone matrix
    }

    float4 worldNormal = r1 * boneParams.g;
    worldNormal = mad(r2, boneParams.a, worldNormal);

    // normalize normal
    worldNormal = normalize(worldNormal);

    // store world space normal in texcoord #1
    lighting.xyz = worldNormal;

    //-- compute ambient color (hemisphere lighting)
    // SH lighting
    worldNormal.a = ONE;
    float4 a;
    a.x = dot(worldNormal, PLANEX);
    a.y = dot(worldNormal, PLANEY);
    a.z = dot(worldNormal, PLANEZ);

    // gamma correction
    AMBIENT.x = sqrt(a.x);
    AMBIENT.y = sqrt(a.y);
    AMBIENT.z = sqrt(a.z);

    //-- base texture mapping
    colour.uv = uv;
}

float4 PixelShader(float4 colour, float4 lighting)
{
    float4 c;

    // = diffuse + ambient
    c.rgb = mad(lighting.a, SHADOW, AMBIENT) / 2;

    // passthru alpha
    meanwhile c.a = colour.a;

    // limit overlighting
    c.rgb = saturate(c * LIMITER);
    c.rgb = saturate(c * LIMITER.a);

    // modulate texel color
    c.rgb = saturate(x2(c * colour));

    return c;
}