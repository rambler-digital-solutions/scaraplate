Rollup Automation
=================

Once you get comfortable with manual rollups, you might want to set up
regularly executed automated rollups.

At this moment scaraplate doesn't provide a CLI for that, but there's
a quite extensible Python code which simplifies implementation of custom
scenarios.

Supported automation scenarios
------------------------------

GitLab Merge Request
++++++++++++++++++++

GitLab integration requires `python-gitlab <https://python-gitlab.readthedocs.io>`_
package, which can be installed with:

::

    pip install 'scaraplate[gitlab]'


Sample ``rollup.py`` script:

::

    from scaraplate import automatic_rollup
    from scaraplate.automation.gitlab import (
        GitLabCloneTemplateVCS,
        GitLabMRProjectVCS,
    )


    automatic_rollup(
        template_vcs_ctx=GitLabCloneTemplateVCS.clone(
            project_url="https://mygitlab.example.org/myorg/mytemplate",
            private_token="your_access_token",
            clone_ref="master",
        ),
        project_vcs_ctx=GitLabMRProjectVCS.clone(
            gitlab_url="https://mygitlab.example.org",
            full_project_name="myorg/mytargetproject",
            private_token="your_access_token",
            changes_branch="scheduled-template-update",
            clone_ref="master",
        ),
    )


This script would do the following:

1. ``git clone`` the template repo to a tempdir;
2. ``git clone`` the project repo to a tempdir;
3. Run ``scaraplate rollup ... --no-input``;
4. Would do nothing if rollup didn't change anything; otherwise it would
   create a commit with the changes, push it to the ``scheduled-template-update``
   branch and open a GitLab Merge Request from this branch.

If a MR already exists, :class:`~scaraplate.automation.gitlab.GitLabMRProjectVCS`
does the following:

1. A one-commit git diff is compared between the already existing MR's branch
   and the locally committed branch (in a tempdir). If diffs are equal,
   nothing is done.
2. If diffs are different, the existing MR's branch is removed from the remote,
   effectively closing the old MR, and a new branch is pushed, which
   is followed by creation of a new MR.

To have this script run daily, crontab can be used. Assuming that the script
is located at ``/opt/rollup.py`` and the desired time for execution is 9:00,
it might look like this:

::

    $ crontab -e
    # Add the following line:
    00 9 * * *  python3 /opt/rollup.py


Git push
++++++++

:class:`~scaraplate.automation.gitlab.GitLabCloneTemplateVCS` and
:class:`~scaraplate.automation.gitlab.GitLabMRProjectVCS` are based off
:class:`~scaraplate.automation.git.GitCloneTemplateVCS` and
:class:`~scaraplate.automation.git.GitCloneProjectVCS`
correspondingly. GitLab classes add GitLab-specific git-clone URL
generation and Merge Request creation. The rest (git clone, commit, push)
is done in the :class:`~scaraplate.automation.git.GitCloneTemplateVCS`
and :class:`~scaraplate.automation.git.GitCloneProjectVCS` classes.

:class:`~scaraplate.automation.git.GitCloneTemplateVCS` and
:class:`~scaraplate.automation.git.GitCloneProjectVCS` classes work
with any git remote. If you're okay with just pushing a branch with
updates (without opening a Merge Request/Pull Request), then you can
use the following:

Sample ``rollup.py`` script:

::

    from scaraplate import automatic_rollup, GitCloneProjectVCS, GitCloneTemplateVCS


    automatic_rollup(
        template_vcs_ctx=GitCloneTemplateVCS.clone(
            clone_url="https://github.com/rambler-digital-solutions/scaraplate-example-template.git",
            clone_ref="master",
        ),
        project_vcs_ctx=GitCloneProjectVCS.clone(
            clone_url="https://mygit.example.org/myrepo.git",
            clone_ref="master",
            changes_branch="scheduled-template-update",
            commit_author="scaraplate <yourorg@yourcompany>",
        ),
    )


Python API
----------

.. autofunction:: scaraplate.automation.base.automatic_rollup

.. autoclass:: scaraplate.automation.base.TemplateVCS
   :show-inheritance:
   :members:

.. autoclass:: scaraplate.automation.base.ProjectVCS
   :show-inheritance:
   :members:

.. autoclass:: scaraplate.automation.git.GitCloneTemplateVCS
   :show-inheritance:
   :members: clone

.. autoclass:: scaraplate.automation.git.GitCloneProjectVCS
   :show-inheritance:
   :members: clone

.. autoclass:: scaraplate.automation.gitlab.GitLabCloneTemplateVCS
   :show-inheritance:
   :members: clone

.. autoclass:: scaraplate.automation.gitlab.GitLabMRProjectVCS
   :show-inheritance:
   :members: clone
