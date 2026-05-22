

all: pdf/ebc-dx.pdf pdf/ebc.pdf pdf/ebc-aln.pdf pdf/ebc-hr-pos.pdf
	

pdf/%.pdf: %.dot
	dot -Tpdf -o $@ $<

clean:
	rm -f pdf/*.pdf

