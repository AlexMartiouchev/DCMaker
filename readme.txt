This project is in extreme alpha stages

Background:
* Most of the viewable work is currently in populator/generation_files/
* Prompts are hidden

Recreate Demo: # currently doesn't work
* Set up Django (install requirements.txt, migrate)
* Create.env file with secret keys:
    OPENAI_API_KEY = xx
    SECRET_KEY = "xx"
* loaddata demo_seed_data.json  
* Optional - Generate and save images using generation_files methods in populator/generation_files/demo_image_generator.py (You will need to replace prompts)
