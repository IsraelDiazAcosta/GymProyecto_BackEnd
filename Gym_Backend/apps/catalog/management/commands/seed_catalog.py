from django.core.management.base import BaseCommand
from apps.catalog.models import Equipment, MuscleGroup, Exercise, ExerciseMuscle

class Command(BaseCommand):
    help = 'Puebla la base de datos con grupos musculares, máquinas principales y ejercicios de ejemplo'

    def handle(self, *args, **options):
        self.stdout.write("Creando grupos musculares...")
        muscles_data = [
            ('Pecho / Pectoral', 'Torso'),
            ('Dorsal / Espalda', 'Torso'),
            ('Deltoides Lateral (Hombro)', 'Hombro'),
            ('Deltoides Anterior (Hombro)', 'Hombro'),
            ('Deltoides Posterior (Hombro)', 'Hombro'),
            ('Bíceps Braquial', 'Brazo'),
            ('Tríceps Braquial', 'Brazo'),
            ('Cuádriceps', 'Pierna'),
            ('Isquiotibiales (Femoral)', 'Pierna'),
            ('Glúteos', 'Pierna'),
            ('Gemelos / Pantorrillas', 'Pierna'),
            ('Abdomen y Core', 'Core'),
        ]

        muscles = {}
        for name, part in muscles_data:
            m, _ = MuscleGroup.objects.get_or_create(name=name, defaults={'body_part': part})
            muscles[name] = m

        self.stdout.write("Creando máquinas y equipamiento...")
        equipment_data = [
            {
                'name': 'Prensa de Piernas a 45°',
                'equipment_type': 'plate_loaded',
                'brand': 'Hammer Strength',
                'description': 'Prensa inclinada con carga de discos. Ideal para enfocar cuádriceps y glúteo.',
                'setup_guide': 'Ajusta el respaldo a 45°. Coloca los pies al ancho de hombros en el centro de la plataforma.'
            },
            {
                'name': 'Polea Alta (Jalón al pecho / Lat Pulldown)',
                'equipment_type': 'cable',
                'brand': 'Life Fitness',
                'description': 'Torre de cable con asiento y rodillos acolchados para fijar los muslos.',
                'setup_guide': 'Ajusta los rodillos para que presionen firmemente tus muslos y no te eleves con el peso.'
            },
            {
                'name': 'Máquina Smith / Multipower',
                'equipment_type': 'smith',
                'brand': 'Matrix',
                'description': 'Barra guiada sobre rieles verticales o ligeramente inclinados con ganchos de seguridad.',
                'setup_guide': 'Coloca los topes de seguridad a la altura deseada antes de comenzar la serie.'
            },
            {
                'name': 'Extensión de Cuádriceps en Máquina',
                'equipment_type': 'pin_selected',
                'brand': 'Technogym',
                'description': 'Máquina de aislamiento con rodillo para la parte inferior de las piernas.',
                'setup_guide': 'Alinea el eje de rotación de la máquina exactamente con la articulación de tus rodillas.'
            },
            {
                'name': 'Curl Femoral Tumbado',
                'equipment_type': 'pin_selected',
                'brand': 'Nautilus',
                'description': 'Máquina para flexión de rodilla tumbado boca abajo para isquiotibiales.',
                'setup_guide': 'El rodillo debe descansar justo encima de los talones (tendón de Aquiles).'
            },
            {
                'name': 'Press de Pecho en Máquina Convergente',
                'equipment_type': 'plate_loaded',
                'brand': 'Hammer Strength',
                'description': 'Palancas independientes con trayectoria convergente para máxima contracción pectoral.',
                'setup_guide': 'Ajusta la altura del asiento para que los agarres queden a la altura media del esternón.'
            },
        ]

        equipments = {}
        for eq_data in equipment_data:
            eq, _ = Equipment.objects.get_or_create(name=eq_data['name'], defaults=eq_data)
            equipments[eq.name] = eq

        self.stdout.write("Creando ejercicios base con máquinas...")
        exercises_data = [
            {
                'name': 'Prensa de Piernas 45°',
                'equipment': equipments['Prensa de Piernas a 45°'],
                'mechanics': 'compound',
                'difficulty': 'beginner',
                'instructions': '1. Siéntate en la máquina apoyando la espalda baja firmemente contra el respaldo.\n2. Coloca los pies en la plataforma.\n3. Empuja la plataforma y desengancha los seguros laterales.\n4. Desciende controladamente hasta flexionar las rodillas a 90 grados sin despegar el glúteo.\n5. Empuja la plataforma hasta la posición inicial sin bloquear las rodillas.',
                'tips': 'No despegues la zona lumbar del asiento en el punto de máxima flexión.',
                'primary_muscle': muscles['Cuádriceps'],
                'secondary_muscle': muscles['Glúteos'],
            },
            {
                'name': 'Jalón al Pecho en Polea Alta',
                'equipment': equipments['Polea Alta (Jalón al pecho / Lat Pulldown)'],
                'mechanics': 'compound',
                'difficulty': 'beginner',
                'instructions': '1. Agarra la barra con un ancho ligeramente superior a los hombros con agarre prono.\n2. Siéntate con los muslos bien encajados bajo los rodillos.\n3. Saca pecho y tira de la barra hacia la parte superior del pecho conduciendo con los codos hacia abajo y atrás.\n4. Controla la subida de forma lenta sintiendo el estiramiento dorsal.',
                'tips': 'Evita balancear el torso excesivamente hacia atrás.',
                'primary_muscle': muscles['Dorsal / Espalda'],
                'secondary_muscle': muscles['Bíceps Braquial'],
            },
            {
                'name': 'Extensión de Rodilla en Máquina',
                'equipment': equipments['Extensión de Cuádriceps en Máquina'],
                'mechanics': 'isolation',
                'difficulty': 'beginner',
                'instructions': '1. Siéntate alineando las rodillas con el eje de giro.\n2. Sujeta las manijas laterales firmemente para estabilizar la cadera.\n3. Extiende las piernas hasta llegar al bloqueo controlado, haciendo una pausa de 1 segundo arriba.\n4. Baja resistiendo la carga de manera excéntrica.',
                'tips': 'Mantén la cadera bien pegada al asiento durante todo el movimiento.',
                'primary_muscle': muscles['Cuádriceps'],
                'secondary_muscle': None,
            },
        ]

        for ex_info in exercises_data:
            primary = ex_info.pop('primary_muscle')
            secondary = ex_info.pop('secondary_muscle')
            ex, created = Exercise.objects.get_or_create(
                name=ex_info['name'],
                defaults=ex_info
            )
            if created:
                ExerciseMuscle.objects.create(exercise=ex, muscle=primary, role='primary')
                if secondary:
                    ExerciseMuscle.objects.create(exercise=ex, muscle=secondary, role='secondary')

        self.stdout.write(self.style.SUCCESS("¡Catálogo base inicializado con éxito!"))

