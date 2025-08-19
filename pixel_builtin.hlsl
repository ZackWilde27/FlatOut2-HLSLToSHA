///////////////////////
// Intrinsic Functions
///////////////////////

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

float4 lerp(x, y, float s)
{
    asm {
        lrp	%0, %3, %2, %1
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

#ifdef float(shaderModel) > 1.1
    float dot(x, y)
    {
        asm {
            dp%tn1	%0, %1, %2
        }
    }
#else
    float dot(x, y)
    {
        asm {
            dp3	%0, %1, %2
        }
    }
#endif


#ifdef float(shaderModel) >= 2.0

    float rsqrt(float x)
    {
        asm {
            rsq %0, %1
        }
    }

    float2 rsqrt(float2 x)
    {
        asm {
            rsq %0.x, %1.x
            rsq %0.y, %1.y
        }
    }

    float3 rsqrt(float3 x)
    {
        asm {
            rsq %0.x, %1.x
            rsq %0.y, %1.y
            rsq %0.z, %1.z
        }
    }

	float4 rsqrt(float4 x)
    {
        asm {
            rsq %0.x, %1.x
            rsq %0.y, %1.y
            rsq %0.z, %1.z
            rsq %0.w, %1.w
        }
    }

    float rcp(float x)
    {
        asm {
            rcp %0, %1
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

	float pow(float x, float y)
	{
		asm {
			pow	%0, %1, %2
		}
	}

	float2 pow(float2 x, float2 y)
	{
		asm {
			pow %0.x, %1.x, %2.x
			pow	%0.y, %1.y, %2.y
		}
	}

	float2 pow(float2 x, float y)
	{
		asm {
			pow %0.x, %1.x, %2
			pow	%0.y, %1.y, %2
		}
	}

	float3 pow(float3 x, float3 y)
	{
		asm {
			pow %0.x, %1.x, %2.x
			pow	%0.y, %1.y, %2.y
			pow	%0.z, %1.z, %2.z
		}
	}

	float3 pow(float3 x, float y)
	{
		asm {
			pow %0.x, %1.x, %2
			pow	%0.y, %1.y, %2
			pow	%0.z, %1.z, %2
		}
	}

	float4 pow(float4 x, float4 y)
	{
		asm {
			pow %0.x, %1.x, %2.x
			pow	%0.y, %1.y, %2.y
			pow	%0.z, %1.z, %2.z
			pow	%0.w, %1.w, %2.w
		}
	}

	float4 pow(float4 x, float y)
	{
		asm {
			pow %0.x, %1.x, %2
			pow	%0.y, %1.y, %2
			pow	%0.z, %1.z, %2
			pow	%0.w, %1.w, %2
		}
	}

	// Calculated as sqrt(dot(value, value))
	float length(float3 value)
	{
		asm {
			dp3	%z.x, %1, %1
			rsq	%z.x, %z.x
			rcp	%0, %z.x
		}
	}


	float3 normalize(float3 v)
	{
		asm {
			nrm	%0, %1
		}
	}

	float4 min(a, b)
	{
		asm {
			min	%0, %1, %2
		}
	}

	float4 max(a, b)
	{
		asm {
			max	%0, %1, %2
		}
	}

	float4 clamp(x, min, max)
	{
		asm {
			min	%z, %1, %3
			max	%0, %z, %2
		}
	}

	float4 saturate(x)
	{
		"%z" = min(x, 1.0f);
		return max("%z", 0.0f);
	}

	float4 abs(x)
	{
		asm {
			abs	%0, %1
		}
	}

	float4 frac(value)
	{
		asm {
			frc	%0, %1
		}
	}

	float exp2(float x)
	{
		asm {
			exp	%0, %1
		}
	}

	float log2(float)
	{
		asm {
			log	%0, %1
		}
	}

	float4 mul(float4 x, mat)
	{
		asm {
			m%tn0x%tn2	%0, %1, %2
		}
	}

	// Have to include the mov unfortunately, since the result depends on the destination swizzle
	float sin(float x)
	{
		asm {
			sincos	%z0.y, %1
			mov	%0, %z0.y
		}
	}

	float cos(float x)
	{
		asm {
			sincos	%z0.x, %1
			mov	%0, %z0.x
		}
	}

	float2 sincos(float x)
	{
		asm {
			sincos	%0, %1
		}
	}

	float3 cross(float3 x, float3 y)
	{
		asm {
			crs	%0, %1, %2
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

	// Calculated as length(x - y)
	float distance(float3 x, float3 y)
	{
		asm {
			sub	%z0, %1, %2
			dp3	%z, %z0, %z0
			rsq	%z, %z
			rcp	%0, %z
		}
	}

	float distance(float2 x, float2 y)
	{
		asm {
			sub	%z0, %1, %2
			mul	%z, %z0.x, %z0.x
			mad %z.w, %z0.y, %z0.y, %z
			rsq	%z, %z
			rcp	%0, %z
		}
	}

	float distance(float x, float y)
	{
		asm {
			sub	%z, %1, %2
			max %0, %z, -%z
		}
	}

	float radians(float x)
	{
		return x * 0.0174533f;
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
		}
		return "%z.x" + 1.0f;
	}

	float4 tex2D(s, float2 t)
	{
		asm {
			texld	%0, %2, %1
		}
	}

	float4 tex2Dbias(s, float4 t)
	{
		asm {
			texldb	%0, %2, %1
		}
	}

	float4 tex2Dbias(s, float4 t)
	{
		asm {
			texldd	%0, %2, %1
		}
	}

	float4 tex2Dlod(s, float4 t)
	{
		asm {
			texldl	%0, %2, %1
		}
	}

	float4 tex2Dproj(s, float4 t)
	{
		asm {
			texldp	%0, %2, %1
		}
	}

	float4 texCUBE(s, float3 t)
	{
		asm {
			texld	%0, %2, %1
		}
	}

	float4 texCUBEbias(s, float4 t)
	{
		asm {
			texldb	%0, %2, %1
		}
	}

	float4 texCUBEgrad(s, float3 t, float3 ddx, float3 ddy)
	{
		asm {
			texldd	%0, %2, %1, %3, %4
		}
	}

	float4 texCUBElod(s, float4 t)
	{
		asm {
			texldl	%0, %2, %1
		}
	}

	float4 texCUBEproj(s, float4 t)
	{
		asm {
			texldp	%0, %2, %1
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

#else

// Uses the formula from pro_water, I don't know the math behind it.
float3 normalize(float3 value)
{
    asm {
        dp3_sat	%z, %1_bx2, %1_bx2
        mad	%0, %1_bias, 1-%z, %1_bx2
    }
}

#endif



////////////////////////////
// Type-Building Functions
////////////////////////////

#ifdef float(shaderModel) >= 2.0

	float2 float2(float x, float y)
	{
		"%0.x" = x;
		"%0.y" = y;
	}

	float2 float2(float x)
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

	float4 float4(float2 xy, float z, float w)
	{
		"%0.xy" = xy;
		"%0.z" = z;
		"%0.w" = w;
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
#else

// Due to the swizzle limitations, only 3 of these can be done in shader model 1
float4 float4(float3 rgb, float a)
{
	"%0.rgb" = rgb;
	meanwhile "%0.a" = a;
}

#endif


float4 float4(float x)
{
	return x;
}

float3 float3(float x)
{
	return x;
}