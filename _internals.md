# Some Internal Items

## Architecture

Let me give you the overview of the structure of handanim.

1. Ops, OpsSet are the core classes that defines the basic operations of drawing, like line to, move to, etc.
2. Drawables are the basic primitives. They implement a draw() method which provides a list of opsset on how to draw those primitives.

- They also have some transformation functions which returns another drawable that modifies its own draw() method to apply the transformations on those opssets.

3. AnimationEvents are objects that takes a drawable object, and a type of animation with start and end duration.
4. In a scene, there are many AnimationEvents objects that takes place.

During rendering, we calculate from the AnimationEvents object,

- which Drawables are currently displayable on screen.
- Then for each Drawable, get the progress for every type of animation assigned to it.
- Call the draw() method of the Drawable to get the opsset that represent it.
- Apply partial progress and transformation to the opsset as required by the animation type.

## 💡 Features to be added

- [x] Linear Arrow
- [ ] Curved Arrow
- [ ] Rounded rect boxes
- [ ] Implementation of flowcharts
- [ ] Import images and videos into scene.
- [ ] Showcasing tabular data
- [ ] Add handwriting curve generating AI model

## Bug fixes to be performed

- [x] Better calculation for bounding box.
- [ ] Autofitting content based on rect boxes.
