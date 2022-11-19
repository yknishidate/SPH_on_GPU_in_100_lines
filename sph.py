import taichi as ti
import math

# Initialize taichi
ti.init(arch=ti.vulkan)
window = ti.ui.Window("SPH", (1024, 1024), vsync=True)
canvas = window.get_canvas()
canvas.set_background_color((1, 1, 1))

num_particles = 1000
radius = 0.03
positions = ti.Vector.field(2, dtype=float, shape=num_particles)
densities = ti.field(dtype=float, shape=num_particles)
pressures = ti.field(dtype=float, shape=num_particles)
velocities = ti.Vector.field(2, dtype=float, shape=num_particles)
accelerations = ti.Vector.field(2, dtype=float, shape=num_particles)
colors = ti.Vector.field(3, dtype=float, shape=num_particles)


@ti.kernel
def initialize():
    for i in ti.grouped(positions):
        positions[i].x = ti.random(float) * 0.2 + 0.4
        positions[i].y = ti.random(float) * 0.8 + 0.1


@ti.func
def spline_kernel(r, h):
    q = ti.math.length(r) / h
    alpha = 10.0 / (7.0 * math.pi * h**2)
    value = 0.0
    if 0.0 <= q <= 1.0:
        value = alpha * (1.0 - 3.0/2.0*q**2 + 3.0/4.0*q**3)
    elif q <= 2.0:
        value = alpha * (1.0/4.0*(2.0 - q)**3)
    return value


@ti.func
def spline_kernel_gradient(r, h):
    q = ti.math.length(r) / h
    alpha = 45.0 / (14.0 * math.pi * h**4)
    value = ti.math.vec2(0.0)
    if 0.0 <= q <= 1.0:
        value = alpha * (q - 4.0/3.0) * r
    elif q <= 2.0:
        value = -(1.0/3.0) * (2.0 - q)**2 * (h / ti.math.length(r)) * r
    return value


@ti.kernel
def update():
    mass = 1.0
    for i in ti.grouped(positions):
        # Compute density
        density = 0.0
        for j in range(num_particles):
            density += mass * spline_kernel(positions[i] - positions[j], radius)
        densities[i] = density

        # Compute pressure
        stiffness = 0.00007
        pressures[i] = max(stiffness * densities[i], 0.0)

    for i in ti.grouped(positions):
        # Compute force
        force = ti.math.vec2(0.0)
        force.y -= 0.98  # gravity
        for j in range(num_particles):
            pi = pressures[i]
            pj = pressures[j]
            grad = spline_kernel_gradient(positions[i] - positions[j], radius)
            force -= mass / densities[j] * (pi + pj) / 2.0 * grad

        # Compute acceleration
        accelerations[i] = force / mass

        # Update velocity / position
        velocities[i] += accelerations[i] * 0.0004  # delta time
        positions[i] += velocities[i]

        # Handle collision
        restitution = 0.4
        if positions[i].x <= 0.0 or 1.0 <= positions[i].x:
            velocities[i].x *= -restitution
            positions[i].x = ti.math.clamp(positions[i].x, 0.01, 0.99)
        elif positions[i].y <= 0.0 or 1.0 <= positions[i].y:
            velocities[i].y *= -restitution
            positions[i].y = ti.math.clamp(positions[i].y, 0.01, 0.99)

        # Compute color
        colors[i].x = pressures[i]


initialize()
while window.running:
    update()
    canvas.circles(positions, radius / 2.0, per_vertex_color=colors)
    window.show()
