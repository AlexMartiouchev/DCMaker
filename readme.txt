This project is in extreme alpha stages

Background:
* Frontend is in development by my partner, who's just learning to code
* Incomplete demo can be accessible throught the generation files folder in the populator app
* Prompts are hidden

Recreate Demo:
* Set up Django (install requirements.txt, migrate)
* Create.env file with secret keys:
    OPENAI_API_KEY = xx
    SECRET_KEY = "xx"
* loaddata demo_seed_data.json
* Optional - Generate and save images using generation_files methods in populator/generation_files/demo_image_generator.py (You will need to replace prompts)
* Open http://localhost:8000/populator/demo/locations