# Трекер задач: GitHub

Задачі й специфікації цього репозиторію живуть як GitHub Issues у
`ruslan-rv-ua/axygen-checklist`. Усі операції — через CLI `gh`.

## Домовленості

- **Створити задачу**: `gh issue create --title "..." --body "..."`. Багаторядкове тіло — через heredoc.
- **Прочитати задачу**: `gh issue view <number> --comments`; коментарі фільтрувати через `jq`, мітки читати звідти ж.
- **Перелічити задачі**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` з потрібними `--label` і `--state`.
- **Прокоментувати**: `gh issue comment <number> --body "..."`
- **Додати / зняти мітку**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Закрити**: `gh issue close <number> --comment "..."`

Репозиторій `gh` визначає сам із `git remote -v`, коли працює всередині клону.

## Pull request'и як поверхня запитів

**PRs as a request surface: no.** — зовнішні PR у чергу тріажу не входять.
_(Прапорець читає `/triage`; постав `yes`, якщо зовнішні PR у цьому репозиторії
слід вважати запитами на функціональність.)_

Якщо `yes`, PR проходять ті самі мітки й стани, що й задачі, командами `gh pr`:

- **Прочитати PR**: `gh pr view <number> --comments`, діф — `gh pr diff <number>`.
- **Перелічити зовнішні PR для тріажу**: `gh pr list --state open --json number,title,body,labels,author,authorAssociation,comments`, лишивши `authorAssociation` зі значенням `CONTRIBUTOR`, `FIRST_TIME_CONTRIBUTOR` або `NONE` (відкинувши `OWNER`/`MEMBER`/`COLLABORATOR`).
- **Коментар / мітка / закриття**: `gh pr comment`, `gh pr edit --add-label`/`--remove-label`, `gh pr close`.

GitHub має спільний простір номерів для задач і PR, тож голе `#42` може бути й
тим, і тим: перевіряй `gh pr view 42` із відкотом на `gh issue view 42`.

## Коли навичка каже «опублікувати в трекері»

Створити GitHub issue.

## Коли навичка каже «взяти відповідний тікет»

Виконати `gh issue view <number> --comments`.

## Операції wayfinding

Їх використовує `/wayfinder`. **Мапа** — одна задача, тікети — **дочірні** задачі.

- **Мапа**: задача з міткою `wayfinder:map`, у тілі якої Notes / Decisions-so-far / Fog. Створення: `gh issue create --label wayfinder:map`.
- **Дочірній тікет**: задача, прив'язана до мапи як GitHub sub-issue (`gh api` на ендпоїнт sub-issues). Де sub-issues не ввімкнено — додати дитину до списку задач у тілі мапи, а на початок тіла дитини поставити `Part of #<map>`. Мітки: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Узятий у роботу тікет призначається на розробника, який його веде.
- **Блокування**: рідні **issue dependencies** GitHub — канонічне подання, видиме в UI. Ребро додається `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, де `<blocker-db-id>` — числовий **database id** блокувальника (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`, _не_ `#number` і не `node_id`). GitHub повертає `issue_dependencies_summary.blocked_by` (лише відкриті блокувальники — це жива умова). Де залежності недоступні, відкіт — рядок `Blocked by: #<n>, #<n>` на початку тіла дитини. Тікет розблоковано, коли закрито всі блокувальники.
- **Запит фронтиру**: перелічити відкриті дочірні задачі мапи (`gh issue list --state open`, обмежившись її sub-issues / списком задач), відкинути ті, що мають відкритий блокувальник (`issue_dependencies_summary.blocked_by > 0` або відкриту задачу в рядку `Blocked by`) чи виконавця; перемагає перша в порядку мапи.
- **Узяти в роботу**: `gh issue edit <n> --add-assignee @me` — перший запис у сесії.
- **Розв'язати**: `gh issue comment <n> --body "<answer>"`, далі `gh issue close <n>`, далі дописати вказівник на контекст (gist + посилання) у Decisions-so-far мапи.
