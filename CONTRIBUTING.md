# Contributing

Правила для авторов (людей и ИИ): docs/adding-new-rules.md (формат правила и секции `### Grep`)
и docs/ai-maintainer.md (порядок работы мейнтейнера).

Перед коммитом

```
python3 scripts/build_index.py
python3 scripts/check_grep.py
```

Индексы `rules/**/INDEX.md` генерируются, вручную их править нельзя.
