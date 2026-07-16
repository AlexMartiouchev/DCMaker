# DCMaker

A D&D campaign content generator. Allows a user to generate fully
built characters and mobs, thematically generated within factions and
locations based on the users inputs. The generation includes stats,
abilities, images, and text.

Built with Django and the OpenAI API.

## Status

Under active rebuild (July 2026). The original prototype (2024) proved
out the idea using regex parsing of free-text LLM responses; the
generation engine is now being rewritten around structured outputs,
which guarantees valid JSON and removes the parsing layer entirely.

## Roadmap

- [ ] Rewrite the generation engine using structured outputs
- [ ] Generator produces and saves a complete demo dataset
- [ ] User-facing generation flow
- [ ] Setup and usage instructions

## Legacy demo

The 2024 prototype demo still lives in the git history - it seeded
pre-generated content from a fixture and browsed it at
`/populator/demo/locations/`.