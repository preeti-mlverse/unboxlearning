"""Development seed data: three accounts and one published course, so anyone can test without setting up by hand.

    .venv/Scripts/python database/seeds/seed.py          (safe to run again: existing rows are left alone)

Accounts (local development only; the seed refuses to run against staging or production):
    creator@unboxed.local   creator and admin of "UnboxEd Demo Workspace"
    learner@unboxed.local   learner, enrolled in the demo course
    admin@unboxed.local     platform admin
Password for all three: SEED_PASSWORD from the environment, or "unboxed-dev-1" by default.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from sqlalchemy import select  # noqa: E402

from unboxed_api.config import get_settings  # noqa: E402
from unboxed_api.db import session_factory, utcnow  # noqa: E402
from unboxed_api.enums import OrgType  # noqa: E402
from unboxed_api.models import Course, Organization, Profile, User  # noqa: E402
from unboxed_api.security import hash_password  # noqa: E402
from unboxed_api.services import courses, learning, orgs  # noqa: E402
from unboxed_api.services.permissions import load_principal  # noqa: E402
from unboxed_api.schemas import CourseCreate  # noqa: E402

PASSWORD = os.environ.get("SEED_PASSWORD", "unboxed-dev-1")

COURSE = {
    "title": "Force and Laws of Motion",
    "description": "Why things start, stop and change direction, from everyday pushes and pulls to Newton's three laws.",
    "modules": [
        ("Motion", [
            ("Describing motion", 5, [
                ("What counts as motion?", "An object is **in motion** when its position changes over time, compared "
                 "with something we treat as still, such as the ground.\n\nA passenger sitting on a moving train is still "
                 "relative to the train, but moving relative to the platform. Motion always depends on what you compare it to."),
                ("Speed and velocity", "**Speed** tells you how fast something moves. **Velocity** adds direction: "
                 "60 km/h north is a velocity, 60 km/h on its own is a speed.\n\n- Speed = distance ÷ time\n- Velocity = "
                 "displacement ÷ time")]),
            ("Acceleration", 6, [
                ("Changing velocity", "**Acceleration** is how quickly velocity changes. Speeding up, slowing down and "
                 "turning a corner are all acceleration, because each changes the velocity.\n\nAcceleration = change in "
                 "velocity ÷ time taken")])]),
        ("Newton's Laws", [
            ("Newton's First Law", 5, [
                ("Things keep doing what they're doing", "An object stays at rest, or keeps moving in a straight line at "
                 "the same speed, unless a force acts on it. This tendency is called **inertia**.\n\nThat's why you lurch "
                 "forward when a bus brakes suddenly: your body keeps moving while the bus slows down.")]),
            ("Newton's Second Law", 6, [
                ("Push harder, speed up faster", "The acceleration of an object depends on the force on it and its mass:\n\n"
                 "**F = m × a**\n\nDouble the force on the same cart and its acceleration doubles. Push a heavier cart with "
                 "the same force and it speeds up more slowly."),
                ("Try it in your head", "Two identical shopping carts. You push one gently and one hard. Which one is moving "
                 "faster after two seconds? The hard push, because a bigger force gives a bigger acceleration.")]),
            ("Newton's Third Law", 5, [
                ("Every action has a partner", "When one object pushes on another, the second pushes back with an equal force "
                 "in the opposite direction.\n\nA swimmer pushes water backwards; the water pushes the swimmer forwards.")])]),
    ],
}


def account(db, email: str, name: str, intent: str, admin: bool = False) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, password_hash=hash_password(PASSWORD), email_verified_at=utcnow(), is_platform_admin=admin)
        user.profile = Profile(display_name=name, signup_intent=intent)
        db.add(user)
        db.flush()
        print(f"  + {email}")
    return user


def main() -> None:
    s = get_settings()
    if s.is_deployed:
        raise SystemExit("The seed is for local development only.")
    db = session_factory()()
    try:
        creator = account(db, "creator@unboxed.local", "Asha Rao", "educator")
        learner = account(db, "learner@unboxed.local", "Ravi Kumar", "learner")
        account(db, "admin@unboxed.local", "Platform Admin", "learner", admin=True)
        org = db.scalar(select(Organization).where(Organization.slug == "unboxed-demo"))
        if org is None:
            org = orgs.create_workspace(db, creator, "UnboxEd Demo Workspace", OrgType.INDEPENDENT_CREATOR)
            org.slug = "unboxed-demo"
            print("  + workspace UnboxEd Demo Workspace")
        p = load_principal(db, creator)
        course = db.scalar(select(Course).where(Course.organization_id == org.id, Course.title == COURSE["title"]))
        if course is None:
            course = courses.create_course(db, p, CourseCreate(title=COURSE["title"], description=COURSE["description"],
                                                               organization_id=org.id))
            for m_title, lessons in COURSE["modules"]:
                module = courses.add_module(db, p, course.id, m_title, "")
                for l_title, minutes, blocks in lessons:
                    lesson = courses.add_lesson(db, p, module.id, l_title, "", minutes)
                    first = lesson.blocks[0]
                    courses.update_block(db, p, first.id, {"heading": blocks[0][0], "body": blocks[0][1]})
                    for heading, body in blocks[1:]:
                        courses.add_block(db, p, lesson.id, "text", {"heading": heading, "body": body})
            db.flush()
            courses.publish(db, p, course.id)
            print(f"  + published course '{course.title}'")
        learning.enroll(db, load_principal(db, learner), course.id)
        db.commit()
        print(f"Seed complete. Log in with any seed account; the password is in {Path(__file__).name}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
