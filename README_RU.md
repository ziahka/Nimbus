<div align="center">
  <img src="https://github.com/hikariatama/assets/raw/master/1326-command-window-line-flat.webp" height="80">
  <h1>Nimbus Userbot</h1>
  <p>Продвинутый юзербот для Telegram с повышенной безопасностью и современными функциями</p>

  <p>
    <a href="https://github.com/ziahka/Nimbus/blob/master/LICENSE">
      <img src="https://img.shields.io/github/license/ziahka/Nimbus" alt="License">
    </a>
    <a href="https://github.com/psf/black">
      <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code Style: Black">
    </a>
    <a href="https://github.com/ziahka/Nimbus/stargazers">
      <img src="https://img.shields.io/github/stars/ziahka/Nimbus?style=flat" alt="Stars">
    </a>
    <br>
    <a href="https://github.com/ziahka/Nimbus/blob/master/README.md">
      <img src="https://img.shields.io/badge/lang-en-red.svg" alt="En">
    </a>
    <a href="https://github.com/ziahka/Nimbus/blob/master/README_RU.md">
      <img src="https://img.shields.io/badge/lang-ru-green.svg" alt="Ru">
    </a>
  </p>

  <p><i>Сделано на основе <a href="https://gitlab.com/hikariatama/Hikka">Hikka</a> от Hikari.</i></p>
</div>

---

## ⚠️ Уведомление о безопасности

> Важное предупреждение о безопасности  
> Хотя Nimbus реализует расширенные меры безопасности, установка модулей от ненадежных разработчиков все еще может нанести вред вашему серверу/аккаунту.
> 
> Рекомендации:
> - ✅ Загружайте модули исключительно из официальных репозиториев или от доверенных разработчиков
> - ❌ НЕ устанавливайте модули, если не уверены в их безопасности
> - ⚠️ Будьте осторожны с неизвестными командами (.terminal, .eval, .ecpp и т.д.)

---
## 🚀 Установка

### VPS/VDS
> **Примечание для пользователей VPS/VDS:**  
> Добавьте `--root` для пользователей root (чтобы избежать ввода force_insecure)

<details>
  <summary><b>Ubuntu / Debian</b></summary>

  ```bash
  sudo apt update && sudo apt install git python3 -y && \
  git clone https://github.com/ziahka/Nimbus.git && \
  cd Nimbus && \
  python3 -m venv .venv && \
  source .venv/bin/activate && \
  pip install -r requirements.txt && \
  python3 -m nimbus
  ```
</details>

<details>
<summary><b>Fedora</b></summary>
  
  ```bash
  sudo dnf update -y && sudo dnf install git python3 -y && \
  git clone https://github.com/ziahka/Nimbus.git && \
  cd Nimbus && \
  python3 -m venv .venv && \
  source .venv/bin/activate && \
  python3 -m pip install -r requirements.txt && \
  python3 -m nimbus
  ```
</details>

<details>
<summary><b>Arch Linux</b></summary>
  
```bash
sudo pacman -Syu --noconfirm && sudo pacman -S git python --noconfirm --needed && \
git clone https://github.com/ziahka/Nimbus.git && \
cd Nimbus && \
python3 -m venv .venv && \
source .venv/bin/activate && \
python3 -m pip install -r requirements.txt && \
python3 -m nimbus
```
</details>



### Другие
<details>
  <summary><b>WSL(Windows)</b></summary>

  > **⚠️ ВНИМАНИЕ: Может быть нестабильно!**

1. **Скачайте WSL.** Для этого откройте PowerShell с правами администратора и введите в консоль
```powershell
wsl --install -d Ubuntu-22.04
```

> *⚠️Для установки требуется Windows 10 сборки 2004 или Windows 11 любой версии и ПК с поддержкой виртуализации.*
> *Для установки на более ранние ОС, пожалуйста, обратитесь к этой [странице](https://learn.microsoft.com/ru-ru/windows/wsl/install-manual).*

2. **Перезагрузите ПК и запустите программу Ubuntu 22.04.x**
3. **Введите эту команду (ПКМ):**
```bash
curl -Ss https://bootstrap.pypa.io/get-pip.py | python3
```
> *⚠️ Если появятся желтые предупреждения, введите export PATH="/home/username/.local/bin:$PATH", заменив /home/username/.local/bin путем, указанным в сообщении*

4. **Введите эту команду (ПКМ):**
```bash
clear && git clone https://github.com/ziahka/Nimbus.git && cd Nimbus && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python3 -m nimbus
```
> **🔗Как получить API_ID и API_HASH?:** [Видео](https://youtu.be/DcqDA249Lhg?t=24)
  
</details>

<details>
  <summary><b>Phone(Userland)</b></summary>
  
 1. <b>Установите UserLAnd по</b> <a href="https://play.google.com/store/apps/details?id=tech.ula">ссылке</a>
2. <b>Откройте его, выберите Ubuntu —> Minimal —> Terminal</b>
3. <b>Дождитесь установки дистрибутива, можете заварить чай</b>
4. <b>После успешной установки перед вами откроется терминал, введите туда:</b>
```bash
sudo apt update && sudo apt upgrade -y && sudo apt install python3 git python3-pip -y && git clone https://github.com/ziahka/Nimbus.git && cd Nimbus && python3 -m venv .venv && source .venv/bin/activate && sudo pip install -r requirements.txt && python3 -m nimbus
```
5. <b>В конце установки появится ссылка, перейдите по ней и введите данные своей учетной записи для входа.</b>
> Вуаля! Вы установили Nimbus на UserLAnd.
</details>

## Дополнительные функции

<details>
  <summary><b>🔒 Автоматическое резервное копирование базы данных</b></summary>
  <img src="https://user-images.githubusercontent.com/36935426/202905566-964d2904-f3ce-4a14-8f05-0e7840e1b306.png" width="400">
</details>

<details>
  <summary><b>👋 Приветственные экраны установки</b></summary>
  <img src="https://user-images.githubusercontent.com/36935426/202905720-6319993b-697c-4b09-a194-209c110c79fd.png" width="300">
  <img src="https://user-images.githubusercontent.com/36935426/202905746-2a511129-0208-4581-bb27-7539bd7b53c9.png" width="300">
</details>

---

## ✨ Ключевые особенности и улучшения

| Особенность | Описание |
|-------------|------------|
| 🪄 Умная команда `.ask` | Опиши, что нужно, обычными словами — Nimbus сам подберёт и выполнит нужную команду. Подробнее ниже |
| 🆕 Последний слой Telegram | Поддержка форумов и новейших функций Telegram |
| 🔒 Повышенная безопасность | Нативное кэширование сущностей и целевые правила безопасности |
| 🎨 Улучшения UI/UX | Современный интерфейс и пользовательский опыт |
| 📦 Основные модули | Улучшенный и новый основной функционал |
| ⏱️ Быстрое исправление ошибок | Более быстрое решение, чем у FTG/GeekTG |
| 🔄 Обратная совместимость | Работает с модулями FTG, GeekTG и Hikka |
| ▶️ Инлайн-элементы | Поддержка форм, галерей и списков |

### 🪄 `.ask` — умная командная строка

Не нужно запоминать точный синтаксис — просто опиши, что нужно сделать:

```text
.ask замьють этот чат на час
.ask покажи кто вступил за последнюю неделю
```

Nimbus смотрит на все команды, загруженные из твоих модулей, просит LLM подобрать
подходящую и нужные аргументы, и перед запуском показывает карточку с подтверждением
(если не отключить этот шаг). Работает с любым OpenAI-совместимым API — самим OpenAI
или любым совместимым провайдером/прокси:

```text
.config SmartCommand api_key <твой ключ>
.config SmartCommand base_url <адрес API, по умолчанию https://api.openai.com/v1>
.config SmartCommand model <название модели, по умолчанию gpt-4o-mini>
.config SmartCommand auto_run <true, чтобы пропускать подтверждение>
```

---

## 📋 Требования

- Python 3.10+
- Учетные данные API из [Telegram Apps](https://my.telegram.org/apps)

---

## 📚 Документация

Отдельного сайта с документацией нет — юзербот документирует себя сам:

- `.help` — список всех загруженных модулей и команд с описанием каждой
- `.help <модуль>` — команды и настройки конкретного модуля
- `.config <модуль>` — просмотр и изменение настроек модуля
- `.dlmod <ссылка или название>` — установка модуля из репозитория или по прямой ссылке
- `.ask <что нужно сделать>` — Nimbus сам найдёт и выполнит нужную команду

---

## 💬 Поддержка

Это небольшой личный форк без отдельного чата поддержки. Нашёл баг или есть предложение —
заведи [issue на GitHub](https://github.com/ziahka/Nimbus/issues) в этом репозитории.

---

## ⚠️ Отказ от ответственности за использование

> Этот проект предоставляется «как есть». Разработчик НЕ несет ответственности за:
> - Блокировки или ограничения аккаунта
> - Удаления сообщений Telegram
> - Проблемы безопасности, вызванные мошенническими модулями
> - Утечки сессий, вызванные вредоносными модулями
>
> Рекомендации по безопасности:
> - Включите .api_fw_protection
> - Избегайте одновременной установки множества модулей
> - Ознакомьтесь с [telegram TOS](https://core.telegram.org/api/terms)

---

## 🙏 Благодарности

- [Hikari](https://gitlab.com/hikariatama) за Hikka (основа проекта)
- [Lonami](https://t.me/lonami) за Telethon
