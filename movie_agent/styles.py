"""Visual style presets. Each gives image-prompt wording and an ffmpeg color grade."""

STYLES = {
    # Ultra-realistic, 8k, natural, clear bright background, high quality camera cinematography
    "realistic": {
        "prompt": (
            "ultra-realistic, 8k resolution, photorealistic, natural skin texture, "
            "clear bright background, high-end professional cinematography, "
            "shot on 85mm full-frame cinema camera, Hasselblad / Arri Alexa, "
            "glamour shot, master studio lighting, crystal clear tack-sharp focus, "
            "pristine high dynamic range, vibrant natural colors, perfectly sharp details, "
            "no noise, no grain, high definition photography"
        ),
        "grade": "eq=contrast=1.06:saturation=1.12:gamma=1.02,unsharp=5:5:0.6:5:5:0.0",
    },
    # Gritty, stylized sword-and-sandal drama: gold dust, deep crimson, hard contrast
    "arena": {
        "prompt": (
            "cinematic still from a gritty stylized historical epic, ancient Roman arena era, "
            "hyper-stylized graphic-novel realism, dust and sweat, hard contrast lighting, "
            "deep crimson and burnt gold palette, desaturated skin tones, dramatic low angle, "
            "shallow depth of field, film grain, 35mm"
        ),
        "grade": "eq=contrast=1.18:saturation=0.82:gamma=0.95,vignette=PI/4,noise=alls=10:allf=t",
    },
    # Lush medieval fantasy TV look: castles, misty forests, soft golden light
    "legend": {
        "prompt": (
            "cinematic still from a medieval fantasy adventure series, ancient castle and misty "
            "green forests, soft golden-hour light, rich earthy colors, flowing cloaks, "
            "painterly realism, shallow depth of field, subtle film grain, 35mm"
        ),
        "grade": "eq=contrast=1.08:saturation=1.05,vignette=PI/5,noise=alls=6:allf=t",
    },
}
DEFAULT_STYLE = "realistic"
