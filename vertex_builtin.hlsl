// The intrinsic functions are no longer hard-coded, to make it easier to change for other games or just in general.


////////////////////////////
// Intrinsic Functions
////////////////////////////

float4 mad(a, b, c)
{
    asm {
        mad	%0, %1, %2, %3
    }
}

float4 fma(a, b, c)
{
    return mad(a, b, c);
}


float dot(float4 x, float4 y)
{
    asm {
        dp4	%0, %1, %2
    }
}

float dot(float3 x, float3 y)
{
    asm {
        dp3	%0, %1, %2
    }
}

float dot(float2 x, float2 y)
{
    float2 that = x * y;
    return that.x + that.y;
}

float exp2(float x)
{
    asm {
        expp	%0, %1
    }
}

float exp2_full(float x)
{
    asm {
        exp	%0, %1
    }
}

float frac(float x)
{
    asm {
        frc	%0, %1
    }
}

float4 max(x, y)
{
    asm {
        max	%0, %1, %2
    }
}

float4 min(x, y)
{
    asm {
        min	%0, %1, %2
    }
}

float log2(float x)
{
    asm {
        logp	%0, %1
    }
}

float log2_full(float x)
{
    asm {
        log	%0, %1
    }
}

float rcp(float x)
{
    asm {
        rcp	%0, %1
    }
}

float2 rcp(float2 x)
{
    asm {
        rcp %0.x, %1.x
        rcp %0.y, %1.y
    }
}

float3 rcp(float3 x)
{
    asm {
        rcp %0.x, %1.x
        rcp %0.y, %1.y
        rcp %0.z, %1.z
    }
}

float4 rcp(float4 x)
{
    asm {
        rcp %0.x, %1.x
        rcp %0.y, %1.y
        rcp %0.z, %1.z
        rcp %0.w, %1.w
    }
}


float rsqrt(float x)
{
    asm {
        rsq	%0, %1
    }
}

float2 rsqrt(float2 x)
{
    asm {
        rsq	%0.x, %1.x
        rsq	%0.y, %1.y
    }
}

float3 rsqrt(float3 x)
{
    asm {
        rsq	%0.x, %1.x
        rsq	%0.y, %1.y
        rsq	%0.z, %1.z
    }
}


float4 rsqrt(float4 x)
{
    asm {
        rsq	%0.x, %1.x
        rsq	%0.y, %1.y
        rsq	%0.z, %1.z
        rsq	%0.w, %1.w
    }
}


float4 dst(float4 x, float4 y)
{
    asm {
        dst	%0, %1, %2
    }
}

#ifdef float(shaderModel) < 2.0

    float abs(float x)
    {
        asm {
            max	%0, %1, -%1
        }
    }

    // Calculated as ((y - x) * s) + x
    float4 lerp(x, y, float s)
    {
        asm {
            sub	%z, %2, %1
            mad	%0, %z, %3, %1
        }
    }

    // Calculated as ((x >= 0) ? 1 : 0) - 0.5 * 2
    float sign(float x)
    {
        "%z.x" = x >= 0 ?;
        "%z.x" -= 0.5f;
        return "%z.x" + "%z.x";
    }

    // Calculated as v / length(v)
    float3 normalize(float v)
    {
        asm {
            dp3	%z0.x, %1, %1
            rsq	%z0.x, %z0.x
            mul	%0, %1, %z0.x
        }
    }

#else

    float abs(float x)
    {
        asm {
            abs %0, %1
        }
    }

    float4 lerp(x, y, float s)
    {
        asm {
            lrp %0, %3, %2, %1
        }
    }

    float4 pow(x, y)
    {
        asm {
            pow %0, %1, %2
        }
    }

    float sign(float x)
    {
        asm {
            sgn %0, %1
        }
    }

    float3 normalize(float3 x)
    {
        asm {
            nrm %0, %1
        }
    }

#endif

float step(float y, float x)
{
    asm {
        sge	%0, %2, %1
    }
}

float radians(float x)
{
    return x * 0.0174533f;
}

// '%z' is just like %0, except it indicates you will read from it later, so if the destination is write-only, a new register is allocated instead.
float sqrt(float x)
{
    asm {
        rsq	%z, %1
        rcp	%0, %z
    }
}

float2 sqrt(float2 x)
{
    asm {
        rsq	%z.x, %1.x
        rcp	%0.x, %z.x
        rsq	%z.y, %1.y
        rcp	%0.y, %z.y
    }
}

float3 sqrt(float3 x)
{
    asm {
        rsq	%z.x, %1.x
        rcp	%0.x, %z.x
        rsq	%z.y, %1.y
        rcp	%0.y, %z.y
        rsq	%z.z, %1.z
        rcp	%0.z, %z.z
    }
}

float4 sqrt(float4 x)
{
    asm {
        rsq	%z.x, %1.x
        rcp	%0.x, %z.x
        rsq	%z.y, %1.y
        rcp	%0.y, %z.y
        rsq	%z.z, %1.z
        rcp	%0.z, %z.z
        rsq	%z.w, %1.w
        rcp	%0.w, %z.w
    }
}

// Calculated as length(x - y)
float distance(float3 x, float3 y)
{
    asm {
        sub	%z0, %1, %2
        dp3	%z.x, %z1, %z1
        rsq	%z.x, %z.x
        rcp	%0, %z.x
    }
}

float distance(float2 x, float2 y)
{
    asm {
        sub	%z, %1, %2
        mul	%z.w, %z.x, %z.x
        mad %z.w, %z.y, %z.y, %z.w
        rsq	%z.w, %z.w
        rcp	%0, %z.w
    }
}

float distance(float x, float y)
{
    asm {
        sub	%z, %1, %2
        max %0, %z, -%z
    }
}


// Calculated as x / 0.0174533f
float degrees(float x)
{
	"%z" = rcp(0.0174533f);
	return "%z" * x;
}

// Calculated as x - frac(x)
float floor(float x)
{
    asm {
        frc	%z, %1
        sub	%0, %1, %z
    }
}

float trunc(float x)
{
    return floor(x);
}


// Calculated as floor(x) + 1
float ceil(float x)
{
    asm {
        frc	%z.x, %1
        sub	%z.x, %1, %z.x
        add	%0, %z.x, c95.y
    }
}

// Calculated as floor(x) + (frac(x) >= 0.5 ? 1 : 0)
float round(float x)
{
    asm {
        frc	%z0.x, %1
        sub	%z0.y, %1, %z0.x
        sge	%z0.z, %z0.x, c95.z
        add	%0, %z0.y, %z0.z
    }
}

float4 lit(float n_dot_l, float n_dot_h, float m)
{
    asm {
        mov	%z.x, %1
        mov	%z.y, %2
        mov	%z.w, %3
        lit	%0, %z
    }
}

// Calculated as x - (floor(x / y) * y)
float fmod(float x, float y)
{
    asm {
        rcp	%z0.x, %2
        mul	%z0.x, %z0.x, %1
        frc	%z0.y, %z0.x
        sub	%z0.x, %z0.x, %z0.y
        mul	%z0.x, %z0.x, %2
        sub	%0, %1, %z0.x
    }
}

// Calculated the same way Microsoft does it: -n * sign(dot(i, ng))
float3 faceforward(float3 n, float3 i, float3 ng)
{
    asm {
        dp3	%z.x, %2, %3
        slt	%z.x, c95.w, %z.x
        sub	%z.x, %z.x, c95.z
        add	%z.x, %z.x, %z.x
        mul	%0, -%1, %z.x
    }
}


// Calculated as i - ((dot(i, n) * 2) * n)
float3 reflect(float3 i, float3 n)
{
    asm {
        dp3	%z.x, %1, %2
        add	%z.x, %z.x, %z.x
        mul	%z, %z.x, %2
        sub	%0, %1, %z
    }
}

// Calculated as sqrt(dot(value, value))
float length(float3 value)
{
    asm {
        dp3	%z0.x, %1, %1
        rsq	%z0.x, %z0.x
        rcp	%0, %z0.x
    }
}

float4 clamp(x, min, max)
{
    asm {
        min	%z, %1, %3
        max	%0, %z, %2
    }
}

float saturate(float x)
{
    return clamp(x, 0.0f, 1.0f);
}

// The %tn2 will be replaced with the second input's number of components
// meanwhile the %tn0 will be replaced with the output's number of components
float4 mul(x, y)
{
    asm {
        m%tn2x%tn0	%0, %1, %2
    }
}

// Calculated as clamp((x - mn) / (mx - mn), 0.0, 1.0)
float smoothstep(float mn, float mx, float x)
{
    asm {
        sub	%z0.x, %2, %1
        rcp	%z0.x, %z0.x
        sub	%z0.y, %3, %1
        mul	%z0.y, %z0.y, %z0.x
        min	%z0.y, %z0.y, c95.y
        max	%0, %z0.y, c95.w
    }
}

// Since cross needed a second place to store information, I finally added local variables to functions, with %z0, %z1, and so on
float3 cross(float3 x, float3 y)
{
    asm {
        mul	%z1, %1.yzx, %2.zxy
        mul	%z0, %1.zxy, %2.yzx
        sub	%0, %z1, %z0
    }
}

////////////////////////////
// Type-Building Functions
////////////////////////////

float2 float2(float x, float y)
{
    "%0.x" = x;
    "%0.y" = y;
}

float2 float2(float x)
{
    return x;
}

float3 float3(float x)
{
    return x;
}

float3 float3(float x, float y, float z)
{
    "%0.x" = x;
    "%0.y" = y;
    "%0.z" = z;
}

float3 float3(float2 xy, float z)
{
    "%0.xy" = xy;
    "%0.z" = z;
}

float4 float4(float x)
{
    return x;
}

float4 float4(float2 xy, float2 zw)
{
    "%0.xy" = xy;
    "%0.zw" = zw;
}

float4 float4(float3 xyz, float w)
{
    "%0.xyz" = xyz;
    "%0.w" = w;
}

float4 float4(float x, float y, float z, float w)
{
    "%0.x" = x;
    "%0.y" = y;
    "%0.z" = z;
    "%0.w" = w;
}

////////////////////////////
// My Intrinsic Functions
////////////////////////////

// With this you can force it to do a dp3 or dp4 instruction with any input
float dot3(x, y)
{
    asm {
        dp3	%0, %1, %2
    }
}

float dot4(x, y)
{
    asm {
        dp4	%0, %1, %2
    }
}

// Returns 1/distance(x, y), so you can '* rdistance()' instead of '/ distance()' for the most efficiency
float rdistance(float3 x, float3 y)
{
    asm {
        sub	%z, %1, %2
        dp3	%z.w, %z, %z
        rsq	%0, %z.w
    }
}

// Same thing as rdistance(), you can '* rlength()' for more efficiency
float rlength(float3 value)
{
    asm {
        dp3	%z.x, %1, %1
        rsq	%0, %z.x
    }
}

// I turned the original fresnel equation into an intrinsic function
// Calculated as pow(1-abs(dot(incident, normal)), around 4 I think)
float fresnel(float3 incident, float3 normal)
{
    asm {
        dp3	%z.x, %1, %2
        max	%z.x, -%z.x, %z.x
        sub	%z.x, c95.y, %z.x
        mul	%z.x, %z.x, %z.x
        mul	%z.x, %z.x, %z.x
        mul	%0, %z.x, %z.x
    }
}




////////////////////////////
// Matrix Stuff
////////////////////////////
float3 RotateToWorld(float3 dir)
{
    asm {
        m3x%tn0	%0, %1, c4
    }
}

float4 LocalToWorld(float4 pos)
{
    asm {
        m4x%tn0	%0, %1, c4
    }
}

float4 LocalToScreen(float4 pos)
{
    asm {
        m4x%tn0	%0, %1, c0
    }
}
