
.PHONY: check-docs
check-docs:
	@# Doesn't generate any output but prints out errors and warnings.
	make -C docs dummy

.PHONY: docs
docs:
	make -C docs html
