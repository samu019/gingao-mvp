from django.db import transaction

from .models import Scene


def _clean(text):
    return " ".join((text or "").split()).strip()


def _duration_distribution(total, count):
    total = max(int(total or 15), count * 2)

    base = total // count
    remainder = total % count

    values = []

    for index in range(count):
        value = base + (1 if index < remainder else 0)
        values.append(max(2, value))

    return values


def _fruit_story(idea):
    idea = _clean(idea)

    return [
        {
            "script":
                "Presentamos a los protagonistas en su entorno. "
                f"La historia parte de esta idea: {idea}",
            "image_prompt":
                "Vertical 9:16 high-quality cinematic 3D cartoon. "
                "Introduce the same anthropomorphic fruit characters "
                "in a bright colorful environment. Consistent faces, "
                "body proportions, colors, arms, legs and expressive eyes.",
            "video_prompt":
                "Animate the characters with subtle natural motion. "
                "Gentle cinematic camera movement. Establish the situation "
                "clearly. Keep character design perfectly consistent."
        },
        {
            "script":
                "Aparece el problema y uno de los personajes reacciona "
                "con miedo o sorpresa.",
            "image_prompt":
                "Vertical 9:16 cinematic 3D cartoon scene. "
                "Show the main fruit character reacting dramatically "
                "to the central problem. Dynamic pose, expressive face, "
                "same character design and same environment.",
            "video_prompt":
                "Animate a quick frightened reaction with natural arm "
                "and leg movement. Subtle tracking camera. No redesign, "
                "no extra limbs, no deformation."
        },
        {
            "script":
                "El personaje busca ayuda y explica urgentemente "
                "lo que esta ocurriendo.",
            "image_prompt":
                "Vertical 9:16 high-quality 3D cartoon. "
                "Two consistent anthropomorphic fruit characters interact. "
                "One looks frightened and asks the other for help.",
            "video_prompt":
                "Animate small urgent hand gestures from the frightened "
                "character. The second character reacts with surprise "
                "and concern. Gentle cinematic push-in."
        },
        {
            "script":
                "Los personajes identifican el peligro y preparan "
                "una solucion.",
            "image_prompt":
                "Vertical 9:16 cinematic 3D cartoon. "
                "Both fruit characters look toward the source of danger. "
                "One points at it while the other becomes determined.",
            "video_prompt":
                "Animate the frightened character pointing toward the "
                "danger. The heroic character changes from surprise to "
                "determination. Smooth subtle motion."
        },
        {
            "script":
                "El personaje valiente actua y se enfrenta al peligro "
                "para intentar salvar la situacion.",
            "image_prompt":
                "Vertical 9:16 dramatic high-quality 3D cartoon. "
                "The heroic fruit character performs a brave dynamic action "
                "toward the danger while the other character watches.",
            "video_prompt":
                "Animate a short heroic action with dynamic forward movement, "
                "subtle motion blur and cinematic camera tracking. "
                "Preserve character consistency."
        },
        {
            "script":
                "Final inesperado y comico que resuelve la historia "
                "de una forma absurda y memorable.",
            "image_prompt":
                "Vertical 9:16 polished cinematic 3D cartoon final scene. "
                "Show the humorous consequence of the story with a clean "
                "visual punchline. Bright lighting, professional composition.",
            "video_prompt":
                "Use a slow cinematic push-in toward the final visual joke. "
                "Minimal movement, comedic timing, polished ending."
        },
    ]


def _short_drama(idea):
    idea = _clean(idea)

    return [
        {
            "script":
                f"Presentacion del protagonista y su situacion: {idea}",
            "image_prompt":
                "Vertical cinematic dramatic establishing shot, "
                "consistent protagonist, emotional lighting.",
            "video_prompt":
                "Slow cinematic movement establishing the protagonist."
        },
        {
            "script":
                "Surge el conflicto principal y cambia la situacion.",
            "image_prompt":
                "Vertical dramatic scene showing the central conflict, "
                "consistent characters and environment.",
            "video_prompt":
                "Natural emotional reactions and subtle camera push-in."
        },
        {
            "script":
                "La tension aumenta y el protagonista debe tomar "
                "una decision importante.",
            "image_prompt":
                "Emotional cinematic close-up, visible tension, "
                "consistent character appearance.",
            "video_prompt":
                "Subtle facial emotion, breathing and slow camera movement."
        },
        {
            "script":
                "El protagonista ejecuta su decision y ocurre "
                "el momento decisivo.",
            "image_prompt":
                "Cinematic climax, strong composition and dramatic action.",
            "video_prompt":
                "Controlled dramatic movement and cinematic tracking."
        },
        {
            "script":
                "La historia termina con una consecuencia clara "
                "o un giro final.",
            "image_prompt":
                "Cinematic ending frame, emotional resolution, "
                "professional vertical composition.",
            "video_prompt":
                "Slow closing camera movement and emotional final beat."
        },
    ]


def _kids_story(idea):
    idea = _clean(idea)

    return [
        {
            "script":
                f"Presentamos a los personajes y su mundo: {idea}",
            "image_prompt":
                "Vertical colorful friendly 3D cartoon for children. "
                "Warm environment and consistent characters.",
            "video_prompt":
                "Gentle happy character motion and smooth camera movement."
        },
        {
            "script":
                "Los personajes descubren un pequeno problema "
                "o una nueva aventura.",
            "image_prompt":
                "Friendly colorful adventure scene with expressive characters.",
            "video_prompt":
                "Animate surprise and curiosity with soft natural motion."
        },
        {
            "script":
                "Intentan resolver el problema juntos.",
            "image_prompt":
                "Positive teamwork scene, bright colors, consistent characters.",
            "video_prompt":
                "Animate cooperative actions and friendly expressions."
        },
        {
            "script":
                "Encuentran la solucion y aprenden algo.",
            "image_prompt":
                "Joyful resolution scene with warm cinematic lighting.",
            "video_prompt":
                "Natural celebration movement and gentle camera push-in."
        },
        {
            "script":
                "Final feliz y visualmente claro.",
            "image_prompt":
                "Colorful happy final frame, polished 3D cartoon aesthetic.",
            "video_prompt":
                "Slow cheerful closing motion."
        },
    ]


def _custom_story(idea):
    idea = _clean(idea)

    return [
        {
            "script":
                f"Introduccion: {idea}",
            "image_prompt":
                "Vertical cinematic establishing image based on the story idea.",
            "video_prompt":
                "Gentle cinematic establishing movement."
        },
        {
            "script":
                "Primer acontecimiento que pone la historia en marcha.",
            "image_prompt":
                "Vertical cinematic scene showing the first major event.",
            "video_prompt":
                "Natural action and subtle camera tracking."
        },
        {
            "script":
                "El conflicto aumenta y obliga al protagonista a reaccionar.",
            "image_prompt":
                "Vertical dramatic scene with clear conflict.",
            "video_prompt":
                "Emotional reaction and controlled cinematic movement."
        },
        {
            "script":
                "Momento decisivo de la historia.",
            "image_prompt":
                "Vertical cinematic climax with strong composition.",
            "video_prompt":
                "Dynamic but controlled climax animation."
        },
        {
            "script":
                "Resolucion y cierre.",
            "image_prompt":
                "Professional vertical final scene with visual resolution.",
            "video_prompt":
                "Slow cinematic final movement."
        },
    ]


GENERATORS = {
    "fruit_story": _fruit_story,
    "short_drama": _short_drama,
    "kids_story": _kids_story,
    "custom": _custom_story,
}


@transaction.atomic
def generate_project_script(project, idea):
    generator = GENERATORS.get(
        project.template_code,
        _custom_story
    )

    definitions = generator(idea)

    durations = _duration_distribution(
        project.target_duration_seconds,
        len(definitions)
    )

    project.scenes.all().delete()

    scenes = []

    for position, definition in enumerate(definitions, start=1):
        scene = Scene.objects.create(
            project=project,
            position=position,
            script=definition["script"],
            image_prompt=definition["image_prompt"],
            video_prompt=definition["video_prompt"],
            duration_seconds=durations[position - 1],
        )

        scenes.append(scene)

    project.status = "script"
    project.save(update_fields=["status", "updated_at"])

    return scenes
