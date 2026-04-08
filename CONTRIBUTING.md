# Contributing to Ghost Auditor

First off, thank you for considering contributing to Ghost Auditor! It's people like you that make it a great tool for everyone.

## Where do I go from here?

If you've noticed a bug or have a question, search the [issue tracker](https://github.com/Boss17536/ghost-auditor/issues) to see if someone else has already documented it. If not, go ahead and make a new issue!

## Fork & create a branch

If this is something you think you can fix, then fork Ghost Auditor and create a branch with a descriptive name.

A good branch name would be (where issue #325 is the ticket you're working on):

```sh
git checkout -b 325-add-new-feature
```

## Get the test suite running

Make sure your environment is properly configured. Check the [README.md](./README.md) for local development setup instructions.

## Implement your fix or feature

At this point, you're ready to make your changes. Please make sure that:
- You document your changes, especially if they are new features or major adjustments to the architecture.
- Follow the existing code style.

## Make a Pull Request

At this point, you should switch back to your master branch and make sure it's up to date with Ghost Auditor's master branch:

```sh
git remote add origin https://github.com/Boss17536/ghost-auditor.git
git checkout master
git pull origin master
```

Then update your feature branch from your local copy of master, and push it!

```sh
git checkout 325-add-new-feature
git rebase master
git push --set-upstream origin 325-add-new-feature
```

Finally, go to GitHub and make a Pull Request!
