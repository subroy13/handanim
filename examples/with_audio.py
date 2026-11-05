import os
from handanim import Circle, Scene, SketchAnimation
from voiceanim import VoiceEngine, VoiceTimelineSync

# 1. Synthesize narration (defaults to Kokoro)
narration = VoiceEngine.synthesize(
    "In our first step, we sketch a circle representing Earth.",
    voice="af_heart",
)

# 2. Synchronize visual event to when "circle" is spoken
circle = Circle(center=(960, 540), radius=100)
event, _ = VoiceTimelineSync.sync_event_to_word(
    clip=narration,
    word="circle",
    event_cls=SketchAnimation,
    drawable=circle,
    duration=1.5,
    lead_in=0.1,  # Start sketching 100ms before "circle" is spoken
)

scene = Scene(width=1920, height=1080)
scene.add(event=event, drawable=circle)

# 3. Render video with audio muxing
# save the scene
output_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "output", "with_audio.mp4"
)

scene.render(output_path, narration=narration)