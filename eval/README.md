# Evaluation

Plumb's accuracy is measured against repos whose right answers are
written down by hand before Plumb runs on them.

`repos.toml` lists the repos. Each gets a folder under `answers/` with an
answer key covering:

- what kind of repo it is
- the services, databases and outside services it uses (service repos)
- the main modules and what each is for
- the setup and test commands
- things a report must not claim

Scores to track on every change:

- **Claim precision:** share of kept claims that are correct.
- **Recall:** share of answer-key items the report covers.
- **Removal rate:** share of model claims the verifier dropped.
