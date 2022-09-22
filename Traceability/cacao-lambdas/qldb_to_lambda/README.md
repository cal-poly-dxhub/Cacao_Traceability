An example of how to package for zip upload to AWS Lambda:
1. `cd /Users/jaronschreiber/.pyenv/versions/3.9.10/envs/cacao-traceability-root/lib/python3.9/site-packages`
2. `zip -r ~/Documents/dxhub/cacao-lambdas/qldb_to_lambda/deployment-package.zip .`
3. `zip -g deployment-package.zip *.py`