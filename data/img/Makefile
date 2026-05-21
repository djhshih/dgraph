# NOTE Use the large versions of the images!

# FIXME  curl does not work because website gatekeeps based on javascript
#        support


all: ebc.jpg ebc-aln.jpg ebc-hr-pos.jpg ebc-tnbc.jpg
	

ebc.jpg:
	curl -L -o $@ https://www.annalsofoncology.org/cms/10.1016/j.annonc.2023.11.016/asset/8d4baab4-7c6b-40eb-b463-219195011475/main.assets/gr2_lrg.jpg

ebc-aln.jpg:
	curl -L -o $@ https://www.annalsofoncology.org/cms/10.1016/j.annonc.2023.11.016/asset/defa22fc-d056-4618-a7ed-aed16ba47109/main.assets/gr3_lrg.jpg

ebc-hr-pos.jpg:
	curl -c cookies.txt -L -o $@ https://www.annalsofoncology.org/cms/10.1016/j.annonc.2023.11.016/asset/9268e903-052e-4be7-99ad-a7af53bfb71b/main.assets/gr4_lrg.jpg

ebc-tnbc.jpg:
	./download.sh 'https://www.annalsofoncology.org/cms/10.1016/j.annonc.2023.11.016/asset/7fce09a5-6ac1-4592-a514-9a6031edbd74/main.assets/gr7_lrg.jpg' ebc-tnbc.jpg
